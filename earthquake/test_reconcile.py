"""Inject semantic faults into in-memory copies after M02 integrity validation."""
import copy
import json
import unittest
from unittest.mock import patch

from earthquake import reconcile


class ReconcileFaults(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = reconcile.load_fixture()

    def setUp(self):
        self.files = list(self.sources)
        self.day = json.loads(self.files[1][1])
        self.rows = self.day["features"]

    def check(self):
        name = self.files[1][0]
        self.files[1] = name, json.dumps(self.day).encode()
        result = reconcile.compare(self.files)
        self.assertFalse(result["agreement"])
        print(self._testMethodName, json.dumps(result, default=str, sort_keys=True))
        return result

    def test_omission(self):
        lost = self.rows.pop()["id"]
        r = self.check()
        self.assertEqual(list(r["missing"]), [lost])
        self.assertIn(self.files[0][0], r["missing"][lost][0]["file"])

    def test_extra_id(self):
        extra = copy.deepcopy(self.rows[0])
        extra["id"] += "-controlled-extra"
        self.rows.append(extra)
        self.assertEqual(list(self.check()["extra"]), [extra["id"]])

    def test_cross_file_duplicate(self):
        other = json.loads(self.files[2][1])["features"][0]
        self.rows.append(other)
        entries = self.check()["duplicates"]["daily"][other["id"]]
        self.assertEqual({e["file"] for e in entries}, {self.files[1][0], self.files[2][0]})

    def test_changed_magnitude(self):
        row = next(f for f in self.rows if f["properties"]["mag"] is not None)
        row["properties"]["mag"] += 1
        r = self.check()
        self.assertFalse(r["missing"] or r["extra"])
        self.assertEqual([(m["id"], m["field"]) for m in r["mismatches"]], [(row["id"], "magnitude")])

    def test_equal_count_replacement(self):
        lost = self.rows[-1]["id"]
        self.rows[-1] = copy.deepcopy(self.rows[0])
        r = self.check()
        self.assertEqual(r["counts"]["daily"], dict(raw=2569, unique=2568, duplicate_ids=1, excess=1))
        self.assertEqual(list(r["missing"]), [lost])
        self.assertEqual(list(r["duplicates"]["daily"]), [self.rows[0]["id"]])
        with patch.object(reconcile, "load_fixture", return_value=self.files):
            self.assertEqual(reconcile.run(), 1)

    def test_invalid_manifest_fails_closed(self):
        with patch.object(reconcile.acquire, "manifest_records", return_value=[]):
            self.assertEqual(reconcile.run(), 1)
