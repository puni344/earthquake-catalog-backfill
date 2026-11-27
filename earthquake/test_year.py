"""Guard the year benchmark's independent partitions and SQLite comparison."""
from contextlib import closing, redirect_stdout
from io import StringIO
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from . import ingest, reconcile, year, year_restart


class YearBenchmarkTests(unittest.TestCase):
    def test_independent_partitions_cover_leap_year(self):
        groups = {r: [(a,b) for role,a,b in year.plan() if role == r] for r in ("reference","ingest")}
        self.assertFalse(set(groups["reference"]) & set(groups["ingest"]))
        for intervals in groups.values():
            self.assertEqual(str(intervals[0][0].date()), "2024-01-01")
            self.assertEqual(str(intervals[-1][1].date()), "2025-01-01")
            self.assertTrue(all(first[1] == second[0] for first,second in zip(intervals, intervals[1:])))

    def test_sql_oracle_rejects_corruption_under_same_id(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            root = Path(tmp)
            db = root / "catalog.sqlite"
            filename, raw = reconcile.load_fixture()[0]
            ingest.ingest(db, lambda *_: None, lambda *_: None)
            with closing(sqlite3.connect(db)) as conn:
                conn.execute("UPDATE observations SET magnitude='999' WHERE rowid=1")
                conn.commit()
            with patch.object(year, "windows", return_value=[({},Path(filename),raw)]):
                with self.assertRaisesRegex(ValueError, "comparison failed"):
                    year_restart.verify_rows(db, root / "oracle.sqlite", root, [])
