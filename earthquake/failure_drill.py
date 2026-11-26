"""Offline injections on disposable copies. Run one named register entry per process."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import errno
import hashlib
import io
import json
import multiprocessing
from pathlib import Path
import shutil
import tempfile
import time
from unittest.mock import patch

from . import acquire, history, ingest, publish_drill, reconcile, restart


class Replay(io.BytesIO):
    status = 200
    headers = {}


def frozen():
    records = acquire.manifest_records(reconcile.MANIFEST)
    return records, list(acquire.verified_bodies(reconcile.MANIFEST.parent, records))


def replay_map():
    records, files = frozen()
    return {r["url"]: raw for r, (_, raw) in zip(records, files)}


def ingest_all(db):
    ingest.ingest(db, lambda *_: None, lambda *_: None)


def measured_transport(bodies):
    calls, transferred = Counter(), Counter()

    def serve(req, **kw):
        url = req.full_url
        calls[url] += 1

        class MeteredReplay(Replay):
            def read(self, size=-1):
                chunk = super().read(size)
                transferred[url] += len(chunk)
                return chunk

        return MeteredReplay(bodies[url])

    return serve, calls, transferred


def killed_acquirer(root, case, conn):
    by_url = replay_map()
    serve, calls, transferred = measured_transport(by_url)
    replace = Path.replace

    def pause(path):
        conn.send((str(path), calls, transferred))
        if not conn.poll(35):
            raise TimeoutError("kill barrier expired")
        raise RuntimeError("unexpected release")

    def partial(response, path):
        with path.open("xb") as out:
            out.write(response.read(512))
            out.flush()
            pause(path)

    def orphan(source, target):
        result = replace(source, target)
        if target.suffix == ".geojson":
            pause(target)
        return result

    injection = (patch.object(acquire, "save_body", partial) if case == "interrupted-fetch"
                 else patch.object(Path, "replace", orphan))
    with conn, injection, patch.object(acquire, "urlopen", side_effect=serve):
        acquire.collect(root/"state", root/"exports")


def acquisition_restart(root, case):
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    proc = ctx.Process(target=killed_acquirer, args=(root, case, child))
    proc.start()
    child.close()
    try:
        restart.require(parent.poll(25), "worker missed barrier")
        path, initial_calls, initial_bytes = parent.recv()
        interrupted = Path(path)
        proc.terminate()
        proc.join(10)
        restart.require(proc.exitcode not in (None, 0), "kill unconfirmed")
        print("TerminateProcess exit", proc.exitcode, "interrupted path", interrupted)
    finally:
        if proc.is_alive():
            proc.kill()
            proc.join(10)
        proc.close()
        parent.close()
    by_url = replay_map()
    first = next(iter(by_url))
    checksum = hashlib.sha256(by_url[first]).hexdigest()
    residue = interrupted.read_bytes()
    print("residue bytes", len(residue), "sha256", hashlib.sha256(residue).hexdigest())
    restart.require(not list(root.rglob("manifest.json")), "partial acquisition marked complete")
    serve, calls, transferred = measured_transport(by_url)
    work, = (root / "state").iterdir()
    with patch.object(acquire, "urlopen", side_effect=serve):
        acquire.collect(root/"state", root/"exports", resume=work.name)
    for phase, counts, sizes in [("initial", initial_calls, initial_bytes), ("restart", calls, transferred)]:
        print(phase, "whole requests", counts[first], "whole bytes", sizes[first],
              "all requests", sum(counts.values()), "all bytes", sum(sizes.values()))
    manifest, = (root/"exports").glob("*/manifest.json")
    records = acquire.manifest_records(manifest)
    acquire.validate(manifest.parent, records)
    print("recovered whole SHA-256", records[0]["sha256"], "expected", checksum,
          "whole requests after restart", calls[first], "total", sum(calls.values()))
    restart.require(records[0]["sha256"] == checksum, "wrong recovered body")
    if case == "orphan-raw":
        restart.require(residue == by_url[first], "orphan corruption")
        restart.require(calls[first] == transferred[first] == 0, "restart fetched the already verified orphan")
    else:
        restart.require(residue == by_url[first][:512] and calls[first] == 1, "wrong partial retry")


def boundary():
    _, files = frozen()
    doc = json.loads(files[0][1])
    features = doc["features"]
    split_ms = features[len(features)//2]["properties"]["time"]
    split = datetime.fromtimestamp(split_ms / 1000, timezone.utc)
    seen = []
    for start, end in [(acquire.START, split), (split, acquire.START + 7*acquire.DAY)]:
        params = acquire.query("daily", start, end)["parameters"]
        lo, hi = [round(datetime.fromisoformat(params[k].replace("Z","+00:00")).timestamp()*1000)
                  for k in ("starttime", "endtime")]
        part = [f for f in features if lo <= f["properties"]["time"] <= hi]
        body = dict(doc, features=part, metadata=dict(doc["metadata"], count=len(part)))
        acquire.inspect(json.dumps(body).encode(), 200, start, end)
        seen.extend(f["id"] for f in part)
        print("inclusive replay bounds", lo, hi, "rows", len(part), "endpoint IDs",
              [f["id"] for f in part if f["properties"]["time"] == split_ms])
    reference = {f["id"] for f in features}
    print("split_ms", split_ms, "missing", sorted(reference-set(seen)), "extra", sorted(set(seen)-reference),
          "duplicate rows", len(seen)-len(set(seen)))
    restart.require(len(seen) == len(reference) and set(seen) == reference, "boundary discrepancy")


def candidate_fault(root, case):
    records, files = frozen()
    manifest = root/"copy"/"manifest.json"
    shutil.copytree(reconcile.MANIFEST.parent, manifest.parent)
    db = root/"catalog.sqlite"
    ingest_all(db)
    old = history.publish(db, 3)
    if case == "drift":
        # Substitute the separately acquired fourth day's real body for the parent.
        # The trial models divergent inputs, not an observed change to USGS.
        record, source = records[0], records[4]
        for key in ("size", "sha256", "features", "acquired_utc"):
            record[key] = source[key]
        record["attempts"][-1]["finished_utc"] = source["acquired_utc"]
        print("Controlled parent replacement. Original capture metadata and actual substitute:",
              json.dumps(acquire.manifest_records(reconcile.MANIFEST)[0]), json.dumps(source))
    else:
        record = records[4]
        body = json.loads(files[4][1])
        event = body["features"][0]
        if case == "missing":
            body["features"].pop(0)
        else:
            body["features"].append(event)
        body["metadata"]["count"] = len(body["features"])
        raw = json.dumps(body).encode()
        record.update(size=len(raw), sha256=hashlib.sha256(raw).hexdigest(), features=len(body["features"]))
        acquire.blob(manifest.parent, record["sha256"]).write_bytes(raw)
        print("injected ID", event["id"], "day", record["start"], "controlled body", record["sha256"])
    manifest.write_text(json.dumps(dict(schema=1, complete=True, responses=records)))
    with patch.object(reconcile, "MANIFEST", manifest):
        checked = list(acquire.verified_bodies(manifest.parent, records))
        result = reconcile.compare([(p.name, raw) for p, raw in checked])
        print("raw counts", result["counts"], "missing", sorted(result["missing"]), "extra", sorted(result["extra"]),
              "duplicates", result["duplicates"]["daily"])
        if case == "missing":
            restart.require(set(result["missing"]) == {event["id"]}, "missing ID undetected")
        elif case == "duplicate":
            restart.require(len(result["duplicates"]["daily"][event["id"]]) == 2, "duplicate undetected")
        else:
            restart.require(result["extra"] and not result["agreement"], "substitution undetected")
        ingest_all(db)
        try:
            history.publish(db, 7)
        except ValueError as error:
            restart.require("scope reconciliation failed" in str(error), "unexpected rejection")
        else:
            raise ValueError("discrepant candidate published")
    restart.require(history.read(db,"current")["id"] == old, "prior publication changed")
    print("publication blocked; current remains", old)


def throttle(root):
    records, files = frozen()
    by_url = {r["url"]: raw for r, (_, raw) in zip(records, files)}
    stamps, urls = [], []

    def serve(req, **kw):
        stamps.append(time.perf_counter())
        urls.append(req.full_url)
        if len(stamps) == 1:
            response = Replay(b"controlled throttling")
            response.status, response.headers = 429, {"Retry-After":"3"}
            return response
        return Replay(by_url[req.full_url])

    with patch.object(acquire, "urlopen", side_effect=serve):
        acquire.collect(root/"state", root/"exports")
    manifest, = (root/"exports").glob("*/manifest.json")
    completed = acquire.manifest_records(manifest)
    acquire.validate(manifest.parent, completed)
    record = completed[0]
    delay = stamps[1]-stamps[0]
    print("attempts", record["attempts"], "elapsed seconds", delay, "final hash", record["sha256"])
    print("verified completion manifest", manifest, "responses", len(completed))
    restart.require(urls == [records[0]["url"]] + list(by_url) and delay >= 3 and record["sha256"] == records[0]["sha256"],
                    "retry did not respect window, backoff or content")


def denied_write(root):
    db = root/"catalog.sqlite"
    ingest_all(db)
    old = history.publish(db, 3)
    before = reconcile.fixture_digest()
    by_url = replay_map()
    original = Path.open

    def deny(path, *args, **kw):
        if path.suffix == ".body" and args == ("xb",):
            raise PermissionError(errno.EACCES, "injected staging-write denial", str(path))
        return original(path, *args, **kw)

    with patch.object(Path, "open", deny), patch.object(acquire, "urlopen",
            side_effect=lambda req, **kw: Replay(by_url[req.full_url])):
        try:
            acquire.collect(root/"state", root/"exports")
        except PermissionError as error:
            print("staging error", repr(error), "errno", error.errno)
            restart.require(error.errno == errno.EACCES, "unexpected errno")
        else:
            raise ValueError("expected staging failure")
    oracle, _ = publish_drill.oracles()
    read = publish_drill.observe(db, "disk", ["current"], {old:oracle})
    print("manifest digest before/after", before, reconcile.fixture_digest(), "read", read)
    restart.require(before == reconcile.fixture_digest() and read["status"] == "success"
                    and not list((root/"exports").glob("*/manifest.json")), "failed preservation")


def run(case):
    with tempfile.TemporaryDirectory(prefix="fault-", dir=restart.state_directory()) as directory:
        root = Path(directory)
        if case in ("orphan-raw","interrupted-fetch"):
            acquisition_restart(root, case)
        elif case in ("missing","duplicate","drift"):
            candidate_fault(root, case)
        elif case == "publish":
            db = root/"catalog.sqlite"
            ingest_all(db)
            old, new = publish_drill.oracles()
            restart.require(history.publish(db, 3) == old["id"], "old ID mismatch")
            publish_drill.incident(db, old, new, "before_pointer")
        elif case == "boundary":
            boundary()
        elif case == "throttle":
            throttle(root)
        elif case == "disk":
            denied_write(root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=["interrupted-fetch","orphan-raw","publish","boundary",
                                         "missing","duplicate","drift","throttle","disk"])
    case = parser.parse_args().case
    try:
        run(case)
    except (ValueError, OSError, EOFError) as error:
        print(f"FAIL {case}: {error}")
        raise SystemExit(1)
    print(f"PASS {case}")
