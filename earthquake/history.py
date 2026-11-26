"""Immutable, scoped USGS publications and a read-only catalog CLI."""
import argparse
import hashlib
import json
import sqlite3
import sys
from contextlib import closing
from decimal import Decimal
from pathlib import Path

from . import acquire, reconcile


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(encode(value).encode("utf-8")).hexdigest()


def magnitude(value):
    if value is None:
        return None
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError(f"invalid magnitude {value}")
    text = format(number, "f")
    if not number:
        return "0"
    return text.rstrip("0").rstrip(".") if "." in text else text


def publish(database, days, *, before_commit=None):
    if days not in (3, 7):
        raise ValueError("supported coverage lengths are 3 and 7 UTC days")
    manifest = reconcile.MANIFEST
    records = acquire.manifest_records(manifest)
    files = list(acquire.verified_bodies(manifest.parent, records))
    selected = records[1:days+1]
    start, end = selected[0]["start"], selected[-1]["end_exclusive"]
    low = int(acquire.START.timestamp()) * 1000
    high = int((acquire.START + days * acquire.DAY).timestamp()) * 1000
    expected = [(key, row) for key, row in reconcile.reference_rows(files[0][0].name, files[0][1])
                if low <= row["event_time"] < high]
    manifest_hash = reconcile.fixture_digest()
    meta = dict(schema=1, fixture=manifest.parent.name, manifest_sha256=manifest_hash,
                start=start, end_exclusive=end, reference_sha256=records[0]["sha256"],
                daily_sources={r["start"][:10]: r["sha256"] for r in selected})

    with closing(sqlite3.connect(database)) as db, db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS publications (
                id TEXT PRIMARY KEY, metadata TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS members (
                publication TEXT NOT NULL, event_id TEXT NOT NULL, event_time INTEGER NOT NULL,
                source_updated INTEGER NOT NULL, magnitude TEXT, PRIMARY KEY(publication,event_id)
            );
            CREATE TABLE IF NOT EXISTS current_publication (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), publication TEXT NOT NULL
            );
        """)
        db.execute("BEGIN IMMEDIATE")
        observed = []
        for index, record in enumerate(selected, 1):
            day = record["start"][:10]
            key = (manifest_hash, day, record["sha256"])
            if not db.execute("SELECT 1 FROM checkpoints WHERE fixture=? AND day=? AND body=?", key).fetchone():
                raise ValueError(f"incomplete scope: missing checkpoint for {day}")
            staged = db.execute("""SELECT id, event_time, source_updated, magnitude, ordinal
                                    FROM observations WHERE fixture=? AND day=? AND body=? ORDER BY ordinal""", key)
            actual = [(eid, dict(event_time=t, source_updated=u, magnitude=None if m is None else Decimal(m),
                                 row=n, file=files[index][0].name)) for eid, t, u, m, n in staged]
            if actual != reconcile.daily_rows([(files[index][0].name, files[index][1])]):
                raise ValueError(f"staging reconciliation failed for {day}")
            observed.extend(actual)
        result = reconcile.compare_rows(expected, observed)
        if not result["agreement"]:
            raise ValueError(f"scope reconciliation failed: {json.dumps(result, default=str)}")
        rows = [dict(event_id=eid, event_time=row["event_time"], source_updated=row["source_updated"],
                     magnitude=magnitude(row["magnitude"])) for eid, row in sorted(observed, key=lambda r: r[0])]
        meta.update(count=len(rows), rows_sha256=digest(rows))
        publication = digest(meta)
        if not db.execute("SELECT 1 FROM publications WHERE id=?", (publication,)).fetchone():
            db.execute("INSERT INTO publications VALUES (?,?)", (publication, encode(meta)))
            db.executemany("INSERT INTO members VALUES (?,?,?,?,?)",
                           ((publication, r["event_id"], r["event_time"], r["source_updated"], r["magnitude"])
                            for r in rows))
        db.execute("""INSERT INTO current_publication VALUES (1,?)
                      ON CONFLICT(singleton) DO UPDATE SET publication=excluded.publication""", (publication,))
        if before_commit is not None:
            before_commit(publication)
    return publication


def read(database, action, publication=None):
    with closing(sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        initialized = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='publications'").fetchone()
        if action == "list":
            if not initialized:
                return []
            return [dict(id=row["id"], **json.loads(row["metadata"])) for row in
                    db.execute("SELECT id,metadata FROM publications ORDER BY rowid")]
        if action == "current":
            current = initialized and db.execute("SELECT publication FROM current_publication WHERE singleton=1").fetchone()
            if not current:
                raise LookupError("no current publication")
            publication = current[0]
        item = initialized and db.execute("SELECT metadata FROM publications WHERE id=?", (publication,)).fetchone()
        if not item:
            raise LookupError(f"unknown publication: {publication}")
        rows = [dict(r) for r in db.execute("""SELECT event_id,event_time,source_updated,magnitude FROM members
                                               WHERE publication=? ORDER BY event_id COLLATE BINARY""", (publication,))]
        return dict(id=publication, rows=rows, **json.loads(item[0]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    actions = parser.add_subparsers(dest="action", required=True)
    actions.add_parser("list")
    actions.add_parser("current")
    actions.add_parser("get").add_argument("id")
    args = parser.parse_args(argv)
    try:
        print(encode(read(args.db, args.action, getattr(args, "id", None))))
    except LookupError as error:
        print(error, file=sys.stderr)
        return 2
    except (OSError, sqlite3.Error, ValueError) as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
