"""Failures in this invocation must override any previous successful drill."""
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from . import demo, verify


class DefaultDemoTests(unittest.TestCase):
    def test_missing_worker_barrier_fails_default_command(self):
        output = StringIO()
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(output), \
                patch.object(demo.restart, "state_directory", return_value=Path(directory)), \
                patch.object(demo.restart, "worker_run", return_value=([("done", "")], 0)):
            self.assertEqual(verify.main([]), 1)
        self.assertIn("October 4 pre-commit crash: ValueError: wrong crash boundary", output.getvalue())
        self.assertIn("Frozen restart correctness: FAIL", output.getvalue())
        self.assertNotIn("M08 PASS", output.getvalue())
