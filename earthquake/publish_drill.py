"""One publisher process termination while four independent CLI reader loops run."""
import json
import math
import multiprocessing
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import acquire, history, ingest, reconcile, restart


def oracles():
    manifest = reconcile.MANIFEST
    records = acquire.manifest_records(manifest)
    files = list(acquire.verified_bodies(manifest.parent, records))
    reference = reconcile.reference_rows(files[0][0].name, files[0][1])
    result = []
    for days in (3, 7):
        low = int(acquire.START.timestamp()) * 1000
        high = int((acquire.START + days * acquire.DAY).timestamp()) * 1000
        rows = [dict(event_id=key, event_time=r["event_time"], source_updated=r["source_updated"],
                     magnitude=history.magnitude(r["magnitude"])) for key, r in sorted(reference)
                if low <= r["event_time"] < high]
        selected = records[1:days+1]
        checksum = history.digest(rows)
        meta = dict(schema=1, fixture=manifest.parent.name, manifest_sha256=reconcile.fixture_digest(),
                    reference_sha256=records[0]["sha256"], start=selected[0]["start"],
                    end_exclusive=selected[-1]["end_exclusive"], count=len(rows), rows_sha256=checksum,
                    daily_sources={r["start"][:10]: r["sha256"] for r in selected})
        result.append(dict(id=history.digest(meta), rows=rows, digest=checksum))
    return result


def check(document, expected):
    publication = document["id"]
    rows = document["rows"]
    checksum = history.digest(rows)
    oracle = expected.get(publication)
    matches = oracle is not None and len(rows) == len(oracle["rows"]) and checksum == oracle["digest"]
    return dict(id=publication, count=len(rows), digest=checksum, status="success" if matches else "mismatch")


def observe(db, reader, args, expected):
    cmd = [sys.executable, "-m", "earthquake.history", "--db", str(db), *args]
    entry = dict(reader=reader, command=subprocess.list2cmdline(cmd), start_utc=acquire.now(),
                 start_ns=time.perf_counter_ns(), exit=None, id=None, count=None, digest=None, error=None)
    try:
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            entry["pid"] = process.pid
            try:
                output, err = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
                raise
            finally:
                entry["exit"] = process.returncode
            if process.returncode:
                raise ValueError(err.decode(errors="replace").strip())
            entry.update(check(json.loads(output), expected))
            if args[0] == "get" and entry["id"] != args[1]:
                entry["status"] = "mismatch"
    except subprocess.TimeoutExpired as error:
        entry.update(status="timeout", error=str(error))
    except (OSError, ValueError, TypeError, KeyError) as error:
        entry.update(status="error", error=str(error))
    entry.update(finish_ns=time.perf_counter_ns(), finish_utc=acquire.now())
    return entry


def paused_publisher(db, channel):
    def barrier(publication):
        channel.send(publication)
        if not channel.poll(45):
            raise TimeoutError("publisher pause expired")
        channel.recv()
        raise RuntimeError("publisher barrier released unexpectedly")
    with channel:
        history.publish(db, 7, before_commit=barrier)


def incident(db, old, new):
    expected = {p["id"]: p for p in (old, new)}
    observations = []
    condition = threading.Condition()
    stop = threading.Event()
    markers = {}

    def mark(name):
        markers[name] = time.perf_counter_ns()
        print(f"MARK {name} ns={markers[name]} utc={acquire.now()}", flush=True)
        return markers[name]

    def loop(identity):
        while not stop.is_set():
            event = observe(db, identity, ["current"], expected)
            with condition:
                observations.append(event)
                condition.notify_all()

    def wait_read(phase, publication):
        with condition:
            found = condition.wait_for(lambda: len({
                r["reader"] for r in observations if r["start_ns"] >= markers[phase]
                and r["id"] == publication and r["status"] == "success"
            }) == 4, timeout=18)
        restart.require(found, f"{phase}: NOT VERIFIED, missing qualifying reader observation")

    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    publisher = ctx.Process(target=paused_publisher, args=(db, child))
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            mark("baseline")
            readers = [pool.submit(loop, i) for i in range(1, 5)]
            try:
                wait_read("baseline", old["id"])
                publisher.start()
                child.close()
                restart.require(parent.poll(20) and parent.recv() == new["id"], "open: NOT VERIFIED")
                mark("open")
                wait_read("open", old["id"])
                mark("kill")
                publisher.terminate()
                publisher.join(10)
                restart.require(publisher.exitcode not in (None, 0), "publisher termination unconfirmed")
                mark("down")
                print(f"publisher_pid={publisher.pid} exit={publisher.exitcode} "
                      f"method={'TerminateProcess' if os.name == 'nt' else 'SIGTERM'}")
                wait_read("down", old["id"])
                mark("retry")
                publication = history.publish(db, 7)
                mark("recovered")
                restart.require(publication == new["id"], "retry returned unexpected ID")
                wait_read("recovered", new["id"])
            finally:
                stop.set()
                for reader in readers:
                    reader.result(timeout=15)
    finally:
        if publisher.pid is not None and publisher.is_alive():
            publisher.kill()
            publisher.join(10)
        publisher.close()
        parent.close()
        child.close()
        counts = {}
        for phase in ("baseline", "open", "kill", "down", "retry", "recovered"):
            counts[phase] = dict(attempts=0, success=0, error=0, timeout=0, mismatch=0)
        for event in sorted(observations, key=lambda r: r["start_ns"]):
            phase = next(name for name in reversed(markers) if markers[name] <= event["start_ns"])
            if event["status"] == "success":
                if (event["finish_ns"] <= markers.get("retry", float("inf")) and event["id"] != old["id"]
                        or event["start_ns"] >= markers.get("recovered", float("inf")) and event["id"] != new["id"]):
                    event.update(status="mismatch", error="wrong current publication for phase")
            counts[phase]["attempts"] += 1
            counts[phase][event["status"]] += 1
            print("READ", json.dumps(dict(event, phase=phase)))
        print("COUNTS (phase at start)", json.dumps(counts))
        coverage = {}
        for phase, boundary, required in (("baseline", "open", old), ("open", "kill", old),
                                          ("down", "retry", old), ("recovered", None, new)):
            verified = len({r["reader"] for r in observations
                            if r["start_ns"] >= markers.get(phase, float("inf"))
                            and r["finish_ns"] <= markers.get(boundary, float("inf"))
                            and r["status"] == "success" and r["id"] == required["id"]}) == 4
            coverage[phase] = verified
            print(f"COVERAGE {phase}: {'VERIFIED' if verified else 'NOT VERIFIED'}")
    restart.require(all(coverage.values()), "missing required phase observation")
    first = min(r["finish_ns"] for r in observations if r["id"] == new["id"] and r["status"] == "success")
    print(f"kill-to-first-verified-new-read={(first-markers['kill'])/1e6:.3f} ms; "
          f"retry-start-to-first-verified-new-read={(first-markers['retry'])/1e6:.3f} ms")
    latencies = sorted((r["finish_ns"]-r["start_ns"])/1e6 for r in observations)
    print("Current CLI observation latency, nearest rank (ms):",
          {p: round(latencies[math.ceil(len(latencies)*p/100)-1], 3) for p in (50, 95)})
    restart.require(all(r["status"] == "success" for r in observations), "reader failure or mismatch")
    for oracle in (old, new):
        event = observe(db, "historical", ["get", oracle["id"]], expected)
        print("FINAL", json.dumps(event))
        restart.require(event["status"] == "success", "historical verification failed")


def run():
    try:
        with tempfile.TemporaryDirectory(prefix="publish-", dir=restart.state_directory()) as directory:
            db = Path(directory) / "catalog.sqlite"
            print(f"fixture={reconcile.MANIFEST.parent.name} database={db}")
            print(f"Monotonic perf_counter resolution={time.get_clock_info('perf_counter').resolution} seconds")
            print("perf_counter_ns markers: kill immediately before terminate; retry immediately before publish; "
                  "recovered after publish returns; read finish after CLI exit, parsing and digest verification.")
            ingest.ingest(db, lambda *_: None, lambda *_: None)
            old, new = oracles()
            for days, oracle in ((3, old), (7, new)):
                print(f"Oracle days={days} id={oracle['id']} count={len(oracle['rows'])} digest={oracle['digest']}")
            restart.require(history.publish(db, 3) == old["id"], "baseline publication mismatch")
            incident(db, old, new)
        print("PASS: publisher process crash, outage reads, retry and both historical IDs verified")
    except (OSError, EOFError, ValueError, sqlite3.Error, TimeoutError) as error:
        print(f"FAIL publish drill: {error}")
        return 1
    return 0
