"""Kill a paused ingestion worker and verify recovery against the frozen parent response."""
import hashlib
import json
import multiprocessing
import os
import sqlite3
from collections import Counter
from contextlib import closing
from decimal import Decimal
from uuid import uuid4

from . import acquire, ingest, preflight, reconcile

TARGET = "2026-10-04"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def state_directory():
    if preflight.run():
        raise ValueError("local state preflight failed")
    return preflight.locations()[1].resolve()


def worker(db, channel, boundary, target, ingestion, inputs):
    def notify(event, day):
        channel.send((event, day))

    def synchronize(position, day):
        if position == boundary and day == target:
            notify("paused-" + position, day)
            channel.recv()  # Only the parent can release this barrier. It terminates us here.
            raise RuntimeError("unexpected release of crash barrier")

    with channel:
        ingestion(db, notify, synchronize, *inputs)
        notify("done", "")


def worker_run(db, boundary=None, *, target=TARGET, ingestion=ingest.ingest, inputs=()):
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe()
    process = context.Process(target=worker, args=(db, child, boundary, target, ingestion, inputs))
    events = []
    process.start()
    child.close()
    try:
        with parent:
            while True:
                require(parent.poll(60), f"worker {process.pid} timed out waiting for signal")
                event, day = parent.recv()
                events.append((event, day))
                if event.startswith("paused-"):
                    require(event == f"paused-{boundary}" and day == target, "unexpected barrier")
                    process.terminate()
                    break
                if event == "done":
                    require(boundary is None, "worker finished without reaching requested barrier")
                    break
        process.join(30)
        require(not process.is_alive(), "worker exit timed out")
        if boundary:
            require(process.exitcode != 0, "paused worker unexpectedly exited successfully")
        else:
            require(process.exitcode == 0, f"ingestion worker failed: {process.exitcode}")
        method = ("TerminateProcess" if os.name == "nt" else "SIGTERM") if boundary else "normal exit"
        print(f"database={db} pid={process.pid} boundary={boundary} target={target} method={method} "
              f"exit={process.exitcode} events={json.dumps(events)}", flush=True)
        return events, process.exitcode
    finally:
        if process.is_alive():
            process.kill()
            process.join()
        process.close()


def snapshot(db):
    with closing(sqlite3.connect(db.as_uri() + "?mode=rw", uri=True)) as conn:
        # Opening a fresh writable connection permits SQLite hot-journal recovery.
        conn.execute("BEGIN")
        marks = conn.execute("SELECT * FROM checkpoints ORDER BY fixture, day, body").fetchall()
        rows = conn.execute("SELECT * FROM observations ORDER BY fixture, day, body, ordinal").fetchall()
    return marks, rows


def days_for(events, kind):
    return [day for event, day in events if event == kind]


def verify_recovered(expected, final_rows, keys):
    observed = []
    for fixture, day, body, ordinal, event_id, origin, updated, mag in final_rows:
        require((fixture, day, body) in keys, "unexpected observation source")
        observed.append((event_id, dict(file=body + ".geojson", row=ordinal, event_time=origin,
                                        source_updated=updated, magnitude=None if mag is None else Decimal(mag))))
    result = reconcile.compare_rows(expected, observed)
    print("Reference vs recovered SQLite rows (daily):", json.dumps(result, default=str, sort_keys=True))
    print(f"Missing IDs={len(result['missing'])}; extra IDs={len(result['extra'])}; "
          f"field mismatches={len(result['mismatches'])}")
    require(result["agreement"], "recovered rows disagree with whole-week reference")
    return result


def crash_case(db, boundary):
    require(not db.exists(), f"expected fresh database: {db}")
    manifest = reconcile.MANIFEST
    records = acquire.manifest_records(manifest)
    files = list(acquire.verified_bodies(manifest.parent, records))
    expected = reconcile.reference_rows(files[0][0].name, files[0][1])
    identity = reconcile.fixture_digest()
    daily = records[1:]
    days = [record["start"][:10] for record in daily]
    keys = [(identity, day, record["sha256"]) for day, record in zip(days, daily)]
    target_index = days.index(TARGET)
    cut = target_index + int(boundary == "after")
    print(f"Fresh database={db} fixture={manifest.parent.name} boundary={boundary}", flush=True)
    events, exit_code = worker_run(db, boundary)
    require(days_for(events, "attempt") == days[:target_index+1]
            and days_for(events, "ack") == days[:target_index], "unexpected pre-kill progress")
    marks, rows = snapshot(db)
    counts = Counter(row[1] for row in rows)
    print(f"Pre-resume checkpoints={[k[1] for k in marks]} rows={dict(counts)} "
          f"target_checkpoint={keys[target_index] in marks} target_rows={counts[TARGET]}")
    require(marks == keys[:cut], "pre-resume checkpoint identities differ")
    require(counts == Counter({days[i]: daily[i]["features"] for i in range(cut)}),
            "pre-resume row counts differ")
    resumed, _ = worker_run(db)
    attempted = days_for(resumed, "attempt")
    skipped = days_for(resumed, "skip")
    require(attempted == days[cut:] and skipped == days[:cut]
            and days_for(resumed, "ack") == attempted, "incorrect resume work")
    replayed = [day for day in attempted if day in days_for(events, "attempt")]
    print(f"Resume attempted={attempted} replayed={replayed} skipped={skipped}")
    final_marks, final_rows = snapshot(db)
    require(final_marks == keys, "incomplete checkpoint set after resume")
    require(final_rows[:len(rows)] == rows, "previously committed observations changed")
    result = verify_recovered(expected, final_rows, keys)
    rerun, _ = worker_run(db)
    require(rerun == [("skip", day) for day in days] + [("done", "")], "completed rerun performed work")
    require(snapshot(db) == (final_marks, final_rows), "completed rerun changed rows or checkpoints")
    print("Completed rerun: all seven skipped; exact ordered checkpoint and observation tuples unchanged")
    return dict(boundary=boundary, termination_exit=exit_code, pre_resume_rows=dict(counts),
                pre_resume_checkpoints=[k[1] for k in marks], replayed=replayed, skipped=skipped,
                attempted=attempted, rerun_skipped=days, rerun_unchanged=True, agreement=True,
                counts=result["counts"], missing=len(result["missing"]), extra=len(result["extra"]),
                mismatches=len(result["mismatches"]))


def run():
    try:
        run_id = uuid4().hex
        directory = state_directory() / "restart" / run_id
        directory.mkdir(parents=True, exist_ok=False)
        print(f"M04 run={run_id} UTC={acquire.now()}")
        cases = []
        for boundary in ("before", "after"):
            try:
                cases.append(crash_case(directory / f"{boundary}.sqlite", boundary))
            except (EOFError, OSError, ValueError, sqlite3.Error) as error:
                print(f"{boundary}: NOT VERIFIED: {error}")
        require(len(cases) == 2, "both crash cases must pass")
        receipt = dict(run_id=run_id, fixture=reconcile.MANIFEST.parent.name,
                       manifest_sha256=reconcile.fixture_digest(), cases=cases, finished_utc=acquire.now())
        path = directory / "result.json"
        path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        print(f"Receipt SHA-256={hashlib.sha256(path.read_bytes()).hexdigest()}\nReceipt: {path}")
        print("Frozen restart correctness: PASS")
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Frozen restart correctness: NOT VERIFIED: {error}")
        return 1
    return 0
