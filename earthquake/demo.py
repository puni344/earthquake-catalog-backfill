"""One offline backfill, crash, recovery and publication history on one SQLite file."""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import platform
import sqlite3
import sys
import tempfile
import threading
import time

from . import acquire, history, ingest, publish_drill, reconcile, restart


class CurrentReaders:
    def __init__(self, db, expected):
        self.db = db
        self.expected = expected
        self.stop = threading.Event()
        self.condition = threading.Condition()
        self.events = []

    def loop(self, reader):
        while not self.stop.is_set():
            event = publish_drill.observe(self.db, reader, ["current"], self.expected)
            with self.condition:
                self.events.append(event)
                self.condition.notify_all()

    def witness(self, phase, publication):
        start = time.perf_counter_ns()

        def observed():
            return any(e["start_ns"] >= start and e["status"] == "success"
                       and e["id"] == publication for e in self.events)

        with self.condition:
            restart.require(self.condition.wait_for(observed, timeout=18),
                            f"{phase}: missing fresh current read of {publication}")
        print(f"WITNESS {phase} since_ns={start} verified_before_ns={time.perf_counter_ns()} id={publication}")


def named_read(db, publication, expected):
    event = publish_drill.observe(db, "by-id", ["get", publication], expected)
    print("BY-ID", json.dumps(event))
    restart.require(event["status"] == "success", f"lookup {publication}: {event}")


def demonstrate(db, verdicts):
    phase = "fixture and acquisition agreement"
    try:
        print(f"fixture={reconcile.MANIFEST.parent.name} database={db} UTC={acquire.now()}")
        files = reconcile.load_fixture()
        agreement = reconcile.compare(files)
        print("Frozen acquisition comparison", json.dumps(agreement, default=str))
        restart.require(agreement["agreement"], "weekly and daily records differ")
        verdicts["Live acquisition agreement"] = "PASS"
        expected = reconcile.reference_rows(*files[0])
        records = acquire.manifest_records(reconcile.MANIFEST)[1:]
        days = [r["start"][:10] for r in records]
        keys = [(reconcile.fixture_digest(), day, r["sha256"]) for day, r in zip(days, records)]
        old, new = publish_drill.oracles()
        oracles = {p["id"]: p for p in (old, new)}

        phase = "October 1-3 publication"
        ingest.ingest(db, lambda event, day: print("seed", event, day), lambda *_: None,
                      through_day=days[2])
        original = restart.snapshot(db)
        restart.require(original[0] == keys[:3], "wrong baseline checkpoints")
        previous = history.publish(db, 3)
        restart.require(previous == old["id"], "incorrect three-day publication")
        named_read(db, previous, oracles)

        readers = CurrentReaders(db, oracles)
        with ThreadPoolExecutor(max_workers=2) as pool:
            tasks = [pool.submit(readers.loop, i) for i in (1, 2)]
            try:
                phase = "baseline readers"
                readers.witness(phase, previous)
                phase = "October 4 pre-commit crash"
                events, _ = restart.worker_run(db, "before")
                restart.require(events == [("skip", d) for d in days[:3]] + [
                    ("attempt", restart.TARGET), ("paused-before", restart.TARGET)], "wrong crash boundary")
                marks, rows = restart.snapshot(db)
                target_rows = sum(r[1] == restart.TARGET for r in rows)
                print("Surviving checkpoints", marks, "October 4 rows", target_rows)
                restart.require((marks, rows) == original and target_rows == 0, "rollback differs from seed")

                phase = "worker down"
                readers.witness(phase, previous)
                phase = "resume and reconcile"
                resumed, _ = restart.worker_run(db)
                restart.require(restart.days_for(resumed, "skip") == days[:3]
                                and restart.days_for(resumed, "attempt") == days[3:]
                                and restart.days_for(resumed, "ack") == days[3:], "unexpected resume events")
                marks, rows = restart.snapshot(db)
                restart.require(marks == keys and rows[:len(original[1])] == original[1],
                                "resume changed baseline or omitted checkpoints")
                restart.verify_recovered(expected, rows, keys)
                verdicts["Frozen restart correctness"] = "PASS"

                phase = "publish recovered week"
                publish_start = time.perf_counter_ns()
                current = history.publish(db, 7, before_commit=lambda _: readers.witness("open publish", previous))
                committed = time.perf_counter_ns()
                restart.require(current == new["id"], "incorrect week publication")
                phase = "post-commit current"
                readers.witness(phase, current)
            finally:
                readers.stop.set()
                for task in tasks:
                    task.result(timeout=15)
                for event in readers.events:
                    print("CURRENT", json.dumps(event))
                counts = Counter(e["status"] for e in readers.events)
                print("Current reader outcomes", {k: counts[k] for k in ("success", "error", "timeout", "mismatch")})
        phase = "current reader verification"
        for event in readers.events:
            restart.require(event["status"] == "success", str(event))
            if event["finish_ns"] <= publish_start or event["start_ns"] >= committed:
                required = previous if event["finish_ns"] <= publish_start else current
                restart.require(event["id"] == required, f"unexpected current ID: {event}")
        phase = "final history"
        for publication in (previous, current):
            named_read(db, publication, oracles)
    except Exception as error:
        if phase == "fixture and acquisition agreement":
            verdicts["Live acquisition agreement"] = "FAIL"
        elif phase in ("October 4 pre-commit crash", "resume and reconcile"):
            verdicts["Frozen restart correctness"] = "FAIL"
        raise RuntimeError(f"{phase}: {type(error).__name__}: {error}") from error


def run():
    start = time.perf_counter()
    verdicts = {"Live acquisition agreement": "NOT RUN", "Frozen restart correctness": "NOT RUN"}
    try:
        print(f"Runtime: {platform.system()} {platform.machine()} | Python {platform.python_version()} | SQLite {sqlite3.sqlite_version}")
        # Preserve the audited Windows volume checks. POSIX uses its private temp directory.
        parent = restart.state_directory() if sys.platform == "win32" else None
        with tempfile.TemporaryDirectory(prefix="demo-", dir=parent) as directory:
            demonstrate(Path(directory) / "catalog.sqlite", verdicts)
    except Exception as error:
        print(f"M08 failure: {error}")
        code = 1
    else:
        code = 0
    for label, verdict in verdicts.items():
        print(f"{label}: {verdict}")
    print(f"M08 {'PASS' if code == 0 else 'FAIL'} elapsed={time.perf_counter()-start:.3f}s")
    return code
