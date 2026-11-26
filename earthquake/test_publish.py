import unittest

from . import history, publish_drill


class ReaderOracleTests(unittest.TestCase):
    def test_old_rows_labelled_with_new_id_fail(self):
        old, new = publish_drill.oracles()
        document = {"id": new["id"], "rows": old["rows"], "count": len(new["rows"]),
                    "rows_sha256": new["digest"]}
        observed = publish_drill.check(document, {p["id"]: p for p in (old, new)})
        self.assertEqual(observed["digest"], history.digest(old["rows"]))
        self.assertEqual(observed["status"], "mismatch")
