"""Exercise actual worker termination and resume on isolated drill databases."""
import tempfile
import unittest
import sqlite3
from contextlib import closing
from pathlib import Path

from . import ingest, restart


class RecoveryTests(unittest.TestCase):
    def exercise(self, boundary, committed, replayed):
        with tempfile.TemporaryDirectory(dir=restart.state_directory()) as folder:
            case = restart.crash_case(Path(folder) / "case.sqlite", boundary)
        self.assertEqual(case["pre_resume_rows"].get("2026-10-04", 0), committed)
        self.assertEqual(case["replayed"], replayed)
        self.assertEqual(case["rerun_skipped"], [f"2026-10-{day:02}" for day in range(1, 8)])
        self.assertTrue(case["agreement"])
        self.assertTrue(case["rerun_unchanged"])

    def test_before_commit(self):
        self.exercise("before", 0, ["2026-10-04"])

    def test_after_commit_before_ack(self):
        self.exercise("after", 383, [])

    def test_foreign_checkpoints_cannot_skip_window(self):
        with tempfile.TemporaryDirectory(dir=restart.state_directory()) as folder:
            db = Path(folder) / "identity.sqlite"
            events = []
            def observe(event, day):
                events.append((event, day))
            def proceed(position, day):
                pass
            ingest.ingest(db, observe, proceed)
            with closing(sqlite3.connect(db)) as connection:
                connection.execute("DELETE FROM observations")
                connection.execute("UPDATE checkpoints SET fixture='other' WHERE day < '2026-10-04'")
                connection.execute("UPDATE checkpoints SET body='other' WHERE day >= '2026-10-04'")
                connection.commit()
            events.clear()
            ingest.ingest(db, observe, proceed)
            self.assertEqual(restart.days_for(events, "skip"), [])
            self.assertEqual(len(restart.days_for(events, "ack")), 7)
