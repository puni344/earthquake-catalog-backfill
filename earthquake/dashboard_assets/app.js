const el = id => document.getElementById(id);
const phases = {idle:"Ready",running:"In progress",paused:"Worker stopped",recovering:"Recovering",complete:"Verified",error:"Failed"};
const labels = {rows:"Rows",missing:"Missing",extra:"Extra",duplicates:"Duplicate rows",mismatches:"Field differences"};
let state, edition, page=0, selection=0, signature="", busy=false;
async function api(path,method="GET"){
  const response=await fetch(path,{method});
  const data=await response.json();
  if(!response.ok) throw Error(data.error || response.statusText);
  return data;
}
function node(tag,text){const item=document.createElement(tag);item.textContent=text;return item;}
function renderRows(){
  const rows=edition?.rows || [], start=page*5;
  el("rows").replaceChildren(...rows.slice(start,start+5).map(row=>{
    const tr=document.createElement("tr");
    for(const value of [row.event_id,new Date(row.event_time).toISOString(),new Date(row.source_updated).toISOString(),row.magnitude ?? "—"]) tr.append(node("td",value));
    return tr;
  }));
  el("range").textContent=rows.length ? (start+1)+"–"+Math.min(start+5,rows.length)+" of "+rows.length+" events" : "";
  el("prev").disabled=page===0;el("next").disabled=start+5>=rows.length;
  el("editionMeta").textContent=edition ? "Publication "+edition.id.slice(0,16)+" · "+edition.start.slice(0,10)+" to "+edition.end_exclusive.slice(0,10)+" (exclusive)" : "Rows will appear after the first publication.";
}
async function read(key){
  const ticket=++selection, run=state.run;
  const doc=await api("/edition/"+run+"/"+key);
  if(ticket!==selection || state.run!==run) return;
  edition=doc;page=0;el("editions").value=doc.id;renderRows();
}
async function refresh(){
  const s=await api("/state");
  if(state?.run!==s.run){selection++;edition=null;signature="";page=0;renderRows();}
  state=s;el("run").disabled=busy || !["idle","complete","error"].includes(s.phase);
  el("run").textContent=s.phase==="complete" || s.phase==="error" ? "Run again" : "Run crash demo";
  el("resume").hidden=s.phase!=="paused";el("resume").disabled=busy;
  el("phase").textContent=phases[s.phase];el("detail").textContent=s.detail;
  el("verdict").textContent=s.phase==="complete"?"PASS":s.phase==="error"?"Failed":"Pending";
  el("days").replaceChildren(...Object.entries(s.days).map(([day,status])=>{
    const d=node("div","");d.className="day";d.dataset.state=status;d.append(node("b",day.slice(-2)),node("span",status));return d;
  }));
  el("metrics").replaceChildren(...Object.entries(labels).map(([k,label])=>{
    const v=node("span","");v.append(node("b",s.result?.[k] ?? "—"),label);return v;
  }));
  const meta=s.editions.find(e=>e.id===s.current);
  el("currentCount").textContent=meta?.count.toLocaleString() ?? "—";
  el("currentMeta").textContent=meta ? meta.id.slice(0,16)+" · "+meta.start.slice(0,10)+" to "+meta.end_exclusive.slice(0,10)+" (exclusive)" : "Awaiting publication";
  el("query").disabled=!meta;el("editions").disabled=!meta;
  const ids=s.editions.map(e=>e.id).join(",");
  if(signature!==ids || !meta){
    signature=ids;el("editions").replaceChildren();
    if(!meta) el("editions").add(new Option("Awaiting first edition",""));
    for(const e of s.editions) el("editions").add(new Option(e.start.slice(5,10)+" → "+e.end_exclusive.slice(5,10)+" exclusive · "+e.count+" rows",e.id));
    if(meta) await read("current");
  }
}
function fail(error){el("error").textContent=error.message;}
async function action(path){
  if(busy)return;busy=true;el("error").textContent="";el("run").disabled=el("resume").disabled=true;
  try{await api(path,"POST");}catch(e){fail(e);}finally{busy=false;}
}
el("run").onclick=()=>action("/start");el("resume").onclick=()=>action("/continue/"+state.run);
el("editions").onchange=e=>read(e.target.value).catch(fail);el("query").onclick=()=>read("current").catch(fail);
el("prev").onclick=()=>{page--;renderRows()};el("next").onclick=()=>{page++;renderRows()};
async function poll(){try{await refresh()}catch(e){fail(e)}setTimeout(poll,300)}poll();

