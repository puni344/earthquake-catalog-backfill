const el = id => document.getElementById(id);
const phases = {idle:"Ready", running:"Ingesting", paused:"Worker stopped", recovering:"Recovering", complete:"Verified", error:"Failed"};
let state, busy = false;
async function request(path, method="GET") {
  const response = await fetch("/annual/"+path, {method});
  const data = await response.json();
  if (!response.ok) throw Object.assign(Error(data.error || response.statusText), {status:response.status});
  return data;
}
function fields(id, entries) {
  const nodes = [];
  for (const [label,value] of entries) {
    const term=document.createElement("dt"), detail=document.createElement("dd");
    term.textContent=label;
    detail.textContent=typeof value==="number" ? value.toLocaleString() : value;
    nodes.push(term,detail);
  }
  el(id).replaceChildren(...nodes);
}
function render(s) {
  state=s;
  el("phase").textContent=s.phase==="idle" && s.start_blocker ? "Waiting for capacity" : phases[s.phase];
  el("detail").textContent=["idle","complete","error"].includes(s.phase) && s.start_blocker ? [s.phase==="idle" ? "" : s.detail,s.start_blocker].filter(Boolean).join(" ") : s.detail;
  el("start").disabled=busy || Boolean(s.start_blocker) || !["idle","complete","error"].includes(s.phase);
  el("resume").hidden=s.phase!=="paused";
  el("resume").disabled=busy;
  const o=s.observation, r=s.result, c=s.comparison;
  fields("observation",o ? [["Interrupted window",o.target],["Worker exit",o.killed_exit],["Committed windows",o.checkpoints],["Surviving rows",o.rows],["Rows from interrupted window",o.target_rows]] : []);
  fields("result",r ? [["Distinct earthquakes",r.unique_events],["Reference rows",c.expected.raw],["Skipped windows",r.skip_windows],["Replayed window",r.replayed.join(", ")],["Replayed rows",r.replayed_rows],["Missing / extra / duplicate rows",[c.missing,c.extra,c.actual.duplicate_rows].join(" / ")],["Records with field differences",c.mismatched_records],["Resume time (seconds)",r.resume_seconds]] : []);
}
async function act(path) {
  if (busy) return;
  busy=true;render(state);el("error").textContent="";
  try { render(await request(path,"POST")); } catch(e) {if(e.status!==429) el("error").textContent=e.message;}
  finally {busy=false;render(state);}
}
el("start").onclick=()=>act("start");
el("resume").onclick=()=>act("continue/"+state.run);
async function poll() {
  try {if (!busy) {const data=await request("state");if (!busy) render(data);}}
  catch(e) {el("error").textContent=e.message;}
  setTimeout(poll,1000);
}
poll();
