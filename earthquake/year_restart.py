"""Measure a forced late worker exit and offline replay against an independent year oracle."""
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
import json
import platform
import sqlite3

from . import acquire, history, ingest, reconcile, restart, year


def year_worker(database, notify, synchronize, folder):
    identity, records = year.read_manifest(folder)
    ingest.ingest_windows(database, identity, year.windows(folder, records, "ingest"), notify, synchronize)


def checkpoints(database):
    with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)) as db:
        return db.execute("SELECT fixture, day, body FROM checkpoints ORDER BY day").fetchall()


def observe_before_resume(database, identity, planned, cut):
    committed = planned[:cut]
    keys = [(identity, r["start"][:10], r["sha256"]) for r in committed]
    restart.require(checkpoints(database) == keys, "unexpected pre-resume checkpoints")
    with closing(sqlite3.connect(database.as_uri() + "?mode=rw", uri=True)) as db:
        counts = dict(db.execute("SELECT day, count(*) FROM observations GROUP BY day"))
    expected = {r["start"][:10]: r["features"] for r in committed if r["features"]}
    restart.require(counts == expected, "pre-resume rows differ from committed windows")
    print("PRE_RESUME", json.dumps(dict(checkpoints=len(keys), rows=sum(counts.values()),
                                       target_rows=counts.get(planned[cut]["start"][:10], 0),
                                       target_checkpoint=False)))


def verify_rows(database, scratch, folder, records):
    with closing(sqlite3.connect(scratch)) as db:
        db.execute("CREATE TABLE expected(id TEXT, event_time INTEGER, source_updated INTEGER, magnitude TEXT)")
        for _, path, raw in year.windows(folder, records, "reference"):
            db.executemany("INSERT INTO expected VALUES(?,?,?,?)", (
                (eid, r["event_time"], r["source_updated"], history.magnitude(r["magnitude"]))
                for eid, r in reconcile.reference_rows(path.name, raw)))
        db.commit()
        db.execute("CREATE INDEX reference_id ON expected(id)")
        db.execute("ATTACH DATABASE ? AS recovered", (str(database),))
        db.create_function("canonical_mag", 1, history.magnitude, deterministic=True)
        # Index a scratch copy so verification leaves the measured database untouched.
        db.execute("CREATE TEMP TABLE actual AS SELECT id,event_time,source_updated,magnitude FROM recovered.observations")
        db.execute("CREATE INDEX temp.actual_id ON actual(id)")
        stats = {}
        for side in ("expected", "actual"):
            raw_count, unique = db.execute(f"SELECT COUNT(*),COUNT(DISTINCT id) FROM {side}").fetchone()
            stats[side] = dict(raw=raw_count, unique=unique, duplicate_rows=raw_count-unique)
        queries = {
            "missing": "SELECT id FROM expected EXCEPT SELECT id FROM actual",
            "extra": "SELECT id FROM actual EXCEPT SELECT id FROM expected",
            "mismatched_records": """SELECT e.id,e.event_time,a.event_time,e.source_updated,a.source_updated,
                                     e.magnitude,a.magnitude FROM expected e JOIN actual a USING(id)
                                     WHERE e.event_time IS NOT a.event_time OR e.source_updated IS NOT a.source_updated
                                     OR e.magnitude IS NOT canonical_mag(a.magnitude)""",
        }
        for issue, query in queries.items():
            stats[issue] = db.execute(f"SELECT COUNT(*) FROM ({query})").fetchone()[0]
            if stats[issue]:
                print(issue, "sample", db.execute(query + " LIMIT 10").fetchall())
        print("RECONCILIATION", json.dumps(stats))
        restart.require(not any(stats[k] for k in queries) and
                        all(stats[s]["duplicate_rows"] == 0 for s in ("actual", "expected")),
                        "Independent reference comparison failed")
        return stats


def benchmark(folder):
    identity, records = year.read_manifest(folder)
    planned = [r for r in records if r["role"] == "ingest"]
    days = [r["start"][:10] for r in planned]
    cut = len(days)-2
    target = days[cut]
    print(f"UTC={acquire.now()} OS={platform.platform()} Python={platform.python_version()} SQLite={sqlite3.sqlite_version}")
    print(f"CAPTURE manifest_sha256={identity} responses={len(records)} bytes={sum(r['size'] for r in records)}")
    with TemporaryDirectory(prefix="year-drill-", dir=folder.parent) as directory:
        database = Path(directory) / "catalog.sqlite"
        args = dict(target=target, ingestion=year_worker, inputs=(folder,))
        first = perf_counter()
        killed, code = restart.worker_run(database, "before", **args)
        kill_seconds = perf_counter()-first
        restart.require(restart.days_for(killed, "attempt") == days[:cut+1]
                        and restart.days_for(killed, "ack") == days[:cut], "wrong initial work")
        observe_before_resume(database, identity, planned, cut)
        first = perf_counter()
        resumed, _ = restart.worker_run(database, **args)
        seconds = perf_counter()-first
        skipped = restart.days_for(resumed, "skip")
        attempted = restart.days_for(resumed, "attempt")
        restart.require(skipped == days[:cut] and attempted == days[cut:]
                        and restart.days_for(resumed, "ack") == attempted, "unexpected resumed work")
        restart.require(checkpoints(database) == [(identity, d, r["sha256"]) for d,r in zip(days, planned)],
                        "incomplete final checkpoint set")
        size = database.stat().st_size
        first = perf_counter()
        stats = verify_rows(database, Path(directory)/"oracle.sqlite", folder, records)
        report = dict(target=target, killed_exit=code, initial_worker_seconds=round(kill_seconds,3),
                      ingestion_bodies_revalidated=len(planned), ingestion_bytes_revalidated=sum(r["size"] for r in planned),
                      skip_windows=len(skipped), replayed=[target], first_attempted=attempted[1:],
                      replayed_rows=planned[cut]["features"], previously_pending_rows=planned[-1]["features"],
                      resume_seconds=round(seconds,3), verification_seconds=round(perf_counter()-first,3),
                      database_bytes=size, unique_events=stats["actual"]["unique"])
        print("YEAR PASS", json.dumps(report))
