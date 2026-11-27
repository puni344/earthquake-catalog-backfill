"""Evaluate a recorded post-attempt current read, or reproduce the offline drill."""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

from . import acquire, history, ingest, publish_drill, reconcile, restart


def check(path):
    """0 = expected publication current, 1 = valid failure signal, 2 = inconclusive."""
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        if record["schema"] != "d2-publication-attempt-v1":
            raise ValueError("unknown signal format")
        expected = record["expected_id"]
        read = record["current_read"]
        if not all(isinstance(key, str) and re.fullmatch("[a-f0-9]{64}", key)
                   for key in (expected, read["id"])):
            raise ValueError("missing or malformed publication ID")
        if read["reader"] != "current" or read["status"] != "success" or read["exit"] != 0:
            raise ValueError("no verified current read")
        if not (0 < record["attempt_finished_ns"] <= read["start_ns"] <= read["finish_ns"]):
            raise ValueError("read did not follow the attempt")
        outcome = record["outcome"]
        if outcome not in ("published", "rejected"):
            raise ValueError("unknown publisher outcome")
    except (KeyError, TypeError, ValueError, OSError) as error:
        print(f"INCONCLUSIVE {path}: {error}")
        return 2
    if outcome == "rejected" or read["id"] != expected:
        print(f"ALERT publication attempt={outcome} expected={expected} current={read['id']}")
        return 1
    print(f"OK expected publication is current: {expected}")
    return 0


def drill(output):
    import platform
    import sqlite3
    import subprocess
    import time

    output.mkdir(parents=True, exist_ok=False)
    print(f"UTC={acquire.now()} machine={platform.platform()} Python={platform.python_version()} "
          f"SQLite={sqlite3.sqlite_version} fixture={reconcile.MANIFEST.parent.name}")
    old, new = publish_drill.oracles()
    oracles = {item["id"]: item for item in (old, new)}
    with tempfile.TemporaryDirectory(dir=restart.state_directory(), prefix="alert-") as work:
        db = Path(work) / "catalog.sqlite"
        def stage(day=None):
            ingest.ingest(db, lambda *args: None, lambda *args: None, through_day=day)

        stage("2026-10-03")
        restart.require(history.publish(db, 3) == old["id"], "baseline publication differs")
        print(f"INJECTION database={db} staged_through=2026-10-03 requested_days=7")
        for label, expected_exit in (("incomplete", 1), ("recovered", 0)):
            if label == "recovered":
                stage()
            reason = None
            try:
                history.publish(db, 7)
                outcome = "published"
            except ValueError as error:
                outcome, reason = "rejected", str(error)
            finished = time.perf_counter_ns()
            read = publish_drill.observe(db, "current", ["current"], oracles)
            record = dict(schema="d2-publication-attempt-v1", expected_id=new["id"],
                          fixture=reconcile.MANIFEST.parent.name, outcome=outcome, reason=reason,
                          attempt_finished_ns=finished, current_read=read)
            path = output / (label + ".json")
            path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            print("SIGNAL", json.dumps(record), flush=True)
            command = [sys.executable, "-m", "earthquake.publication_alert", "check", str(path)]
            print("COMMAND", subprocess.list2cmdline(command), flush=True)
            status = subprocess.run(command, timeout=15).returncode
            print(f"checker_exit={status}")
            restart.require(status == expected_exit, "unexpected alert verdict")
            if label == "incomplete":
                restart.require(reason == "incomplete scope: missing checkpoint for 2026-10-04"
                                and read["id"] == old["id"], "injection boundary not observed")
    print("PASS: publication failure detected and retry verified")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("check").add_argument("record", type=Path)
    sub.add_parser("drill").add_argument("new_output_directory", type=Path)
    args = parser.parse_args()
    if args.action == "check":
        return check(args.record)
    drill(args.new_output_directory)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
