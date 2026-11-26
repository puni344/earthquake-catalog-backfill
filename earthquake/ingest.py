"""Ingest verified daily windows into a fixture-scoped SQLite database."""
import sqlite3
from contextlib import closing

from . import acquire, reconcile


def ingest(database, notify, synchronize):
    manifest = reconcile.MANIFEST
    fixture = reconcile.fixture_digest()
    records = acquire.manifest_records(manifest)
    with closing(sqlite3.connect(database)) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS checkpoints (
                fixture TEXT, day TEXT, body TEXT, PRIMARY KEY(fixture, day, body)
            );
            CREATE TABLE IF NOT EXISTS observations (
                fixture TEXT, day TEXT, body TEXT, ordinal INTEGER, id TEXT,
                event_time INTEGER, source_updated INTEGER, magnitude TEXT,
                PRIMARY KEY(fixture, day, body, ordinal)
            );
        """)
        for index, (path, raw) in enumerate(acquire.verified_bodies(manifest.parent, records)):
            record = records[index]
            if record["role"] != "daily":
                continue
            day = record["start"][:10]
            key = fixture, day, record["sha256"]
            # Lock before the skip decision so two workers cannot both claim this window.
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM checkpoints WHERE fixture=? AND day=? AND body=?", key).fetchone():
                db.rollback()
                notify("skip", day)
                continue
            notify("attempt", day)
            for event_id, row in reconcile.daily_rows([(path.name, raw)]):
                mag = row["magnitude"]
                db.execute("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?)",
                           (*key, row["row"], event_id, row["event_time"], row["source_updated"],
                            None if mag is None else str(mag)))
            db.execute("INSERT INTO checkpoints VALUES (?,?,?)", key)
            synchronize("before", day)
            db.commit()
            synchronize("after", day)
            notify("ack", day)
