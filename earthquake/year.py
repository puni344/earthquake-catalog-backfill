"""Capture the 2024 ComCat catalog through two independent query partitions."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from . import acquire


def plan():
    begin = datetime(2024, 1, 1, tzinfo=timezone.utc)
    stop = datetime(2025, 1, 1, tzinfo=timezone.utc)
    for role, width in (("reference", 12), ("ingest", 7)):
        start = begin
        while start < stop:
            end = min(start + width * acquire.DAY, stop)
            yield role, start, end
            start = end


def name(role, start):
    return f"{role}-{start.date()}"


def capture(folder):
    folder.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(folder / "capture-lock.sqlite", timeout=0)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        collect(folder)


def collect(folder):
    if (folder / "manifest.json").exists():
        raise ValueError("Capture already sealed; use a fresh directory")
    records = []
    for role, start, end in plan():
        base = name(role, start)
        receipt = folder / (base + ".json")
        path = folder / (base + ".body")
        if receipt.exists():
            record = json.loads(receipt.read_bytes())
        else:
            stage = folder / ("attempt-" + uuid4().hex)
            stage.mkdir()
            record, body = acquire.fetch(stage, role, start, end)
            body.replace(path)
            temp = receipt.with_suffix(".pending")
            temp.write_text(json.dumps(record), encoding="utf-8")
            temp.replace(receipt)
        acquire.check_response(path, record, role, start, end)
        records.append(record)
    temp = folder / "manifest.pending"
    temp.write_text(json.dumps(records, indent=2), encoding="utf-8")
    temp.replace(folder / "manifest.json")
    print("Sealed", len(records), "independent response bodies")


def read_manifest(folder):
    raw = (folder / "manifest.json").read_bytes()
    records = json.loads(raw)
    if len(records) != len(list(plan())):
        raise ValueError("Incomplete year manifest")
    return hashlib.sha256(raw).hexdigest(), records


def windows(folder, records, wanted):
    for (role, start, end), record in zip(plan(), records):
        if role == wanted:
            path = folder / (name(role, start) + ".body")
            yield record, path, acquire.check_response(path, record, role, start, end)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["capture", "verify"])
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    if args.action == "capture":
        capture(args.folder)
    else:
        from .year_restart import benchmark
        benchmark(args.folder.resolve())


if __name__ == "__main__":
    main()
