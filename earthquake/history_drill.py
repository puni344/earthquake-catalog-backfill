"""Verify fresh reader processes against an independently filtered whole-week oracle."""
import json
import sqlite3
import subprocess
import sys
from decimal import Decimal
from uuid import uuid4

from . import acquire, history, restart, reconcile, ingest


def reader(db, *args, expected_exit=0):
    cmd = [sys.executable, "-m", "earthquake.history", "--db", str(db), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    print(f"{acquire.now()} $ {subprocess.list2cmdline(cmd)}\nexit={result.returncode}", flush=True)
    if result.stderr:
        print(result.stderr.rstrip())
    restart.require(result.returncode == expected_exit, "unexpected reader exit")
    if result.returncode == 0:
        return json.loads(result.stdout)


def verify_read(document, expected, publication, sources):
    restart.require(document["id"] == publication, "incorrect publication ID")
    restart.require((document["start"], document["end_exclusive"]) ==
                    (sources[0]["start"], sources[-1]["end_exclusive"]), "incorrect scope")
    restart.require(document["daily_sources"] == {r["start"][:10]: r["sha256"] for r in sources},
                    "incorrect source provenance")
    rows = document["rows"]
    restart.require(len(rows) == len(expected) == document["count"], "incorrect row count")
    for actual, (eid, oracle) in zip(rows, expected):
        mag = actual["magnitude"]
        values = (actual["event_id"], actual["event_time"], actual["source_updated"],
                  None if mag is None else Decimal(mag))
        restart.require(values == (eid, oracle["event_time"], oracle["source_updated"], oracle["magnitude"]),
                        f"returned row differs from whole-week reference: {eid}")
    measured = history.digest(rows)
    restart.require(measured == document["rows_sha256"], "digest of returned rows differs from metadata")
    print(f"Verified id={publication} coverage=[{document['start']},{document['end_exclusive']}) "
          f"rows={len(rows)} returned_rows_sha256={measured}")
    return measured


def run():
    try:
        directory = restart.state_directory() / "history" / uuid4().hex
        directory.mkdir(parents=True, exist_ok=False)
        db = directory / "catalog.sqlite"
        print(f"{acquire.now()} history database={db} fixture={reconcile.MANIFEST.parent.name}")
        ingest.ingest(db, lambda event, day: print(f"ingest {event} {day}"), lambda *_: None)
        files = reconcile.load_fixture()
        reference = sorted(reconcile.reference_rows(*files[0]), key=lambda pair: pair[0])
        records = acquire.manifest_records(reconcile.MANIFEST)[1:]
        def scope(days):
            low = int(acquire.START.timestamp()) * 1000
            high = int((acquire.START + days * acquire.DAY).timestamp()) * 1000
            return [pair for pair in reference if low <= pair[1]["event_time"] < high]

        short, full = scope(3), scope(7)
        restart.require(reader(db, "list") == [], "fresh history should be empty")
        reader(db, "current", expected_exit=2)
        old = history.publish(db, 3)
        initial = verify_read(reader(db, "current"), short, old, records[:3])
        new = history.publish(db, 7)
        restart.require(old != new and len(short) < len(full), "expected distinguishable publications")
        listing = reader(db, "list")
        restart.require([p["id"] for p in listing] == [old, new], "unexpected publication listing")
        print("Listing:", json.dumps(listing, sort_keys=True))
        current = verify_read(reader(db, "current"), full, new, records)
        earlier = verify_read(reader(db, "get", old), short, old, records[:3])
        later = verify_read(reader(db, "get", new), full, new, records)
        restart.require(initial == earlier and current == later, "inconsistent reader digests")
        reader(db, "get", "unknown-m05", expected_exit=2)
        print("PASS: shorter publication preserved; current and newer named read agree")
    except (OSError, ValueError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
        print(f"FAIL history: {error}")
        return 1
    return 0
