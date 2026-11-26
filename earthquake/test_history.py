"""Publication gates and historical reads against disposable real-data databases."""
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from . import history, ingest


class HistoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.db = Path(directory.name) / "catalog.sqlite"
        ingest.ingest(self.db, lambda *_: None, lambda *_: None)

    def test_empty_history(self):
        self.assertEqual(history.read(self.db, "list"), [])
        with self.assertRaisesRegex(LookupError, "no current publication"):
            history.read(self.db, "current")

    def test_unknown_id(self):
        history.publish(self.db, 3)
        with self.assertRaisesRegex(LookupError, "unknown publication: missing-id"):
            history.read(self.db, "get", "missing-id")

    def test_incomplete_window_blocks_pointer_change(self):
        old = history.publish(self.db, 3)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("DELETE FROM checkpoints WHERE day='2026-10-05'")
        with self.assertRaisesRegex(ValueError, "2026-10-05"):
            history.publish(self.db, 7)
        self.assertEqual([p["id"] for p in history.read(self.db, "list")], [old])
        self.assertEqual(history.read(self.db, "current")["id"], old)

    def test_damaged_staging_cannot_change_published_values(self):
        old = history.publish(self.db, 3)
        initial = history.read(self.db, "get", old)
        with closing(sqlite3.connect(self.db)) as db, db:
            db.execute("UPDATE observations SET magnitude='99' WHERE ordinal=1")
        with self.assertRaisesRegex(ValueError, "reconciliation"):
            history.publish(self.db, 7)
        self.assertEqual(initial, history.read(self.db, "current"))

    def test_older_lookup_after_new_publication(self):
        old = history.publish(self.db, 3)
        initial = history.read(self.db, "current")
        new = history.publish(self.db, 7)
        newer = history.read(self.db, "current")
        self.assertEqual(newer["id"], new)
        self.assertNotEqual(old, new)
        self.assertLess(len(initial["rows"]), len(newer["rows"]))
        self.assertEqual(history.read(self.db, "get", old), initial)
        self.assertEqual(history.publish(self.db, 7), new)
        self.assertEqual(len(history.read(self.db, "list")), 2)
