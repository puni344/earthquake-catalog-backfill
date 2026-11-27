"""Check the recorded-signal decision independently of the injection driver."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from earthquake.publication_alert import check


class PublicationAlertTest(unittest.TestCase):
    def test_recorded_failure_and_recovery(self):
        evidence = Path(__file__).resolve().parents[1] / "docs/evidence/task-5-publication-alert"
        self.assertEqual(check(evidence / "incomplete.json"), 1)
        self.assertEqual(check(evidence / "recovered.json"), 0)

    def test_wrong_current_and_unusable_observations(self):
        record = dict(schema="d2-publication-attempt-v1", expected_id="a"*64,
                      outcome="published", attempt_finished_ns=10,
                      current_read=dict(reader="current", status="success", exit=0,
                                        id="b"*64, start_ns=11, finish_ns=12))
        with TemporaryDirectory() as folder:
            path = Path(folder) / "signal.json"
            self.assertEqual(check(path), 2)
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(check(path), 1)
            record["current_read"]["start_ns"] = 9
            path.write_text(json.dumps(record), encoding="utf-8")
            self.assertEqual(check(path), 2)
