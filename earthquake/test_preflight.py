"""Controlled failures use temporary directories and never change host resources."""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from earthquake import preflight
from earthquake.verify import main


class PreflightFailures(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.state = self.base / "local" / "D2" / "state"
        self.root = self.base / "OneDrive"
        self.repo = self.base / "repo"

    def reject(self, expected, *, python="3.10.11", sqlite="3.40.1", state=None,
               total=8192, available=4096, disk=2048):
        output = io.StringIO()
        with patch.object(preflight, "native_windows", return_value=True), \
             patch.object(preflight.platform, "python_version", return_value=python), \
             patch.object(preflight.sqlite3, "sqlite_version", sqlite), \
             patch.object(preflight, "locations", return_value=(
                 self.base, state or self.state, self.repo, [self.root])), \
             patch.object(preflight, "capacity", return_value=(
                 total * 2**20, available * 2**20, 8, disk * 2**20)), \
             patch.object(preflight, "sqlite_probe") as probe, redirect_stdout(output):
            code = main(["--drill", "preflight"])
        self.assertNotEqual(code, 0)
        self.assertIn(expected, output.getvalue())
        probe.assert_not_called()
        print(f"controlled exit={code} | {output.getvalue().splitlines()[-1]}")

    def test_python_mismatch(self):
        self.reject("Python 3.11.0", python="3.11.0")

    def test_sqlite_mismatch(self):
        self.reject("SQLite 3.40.0", sqlite="3.40.0")

    def test_repository_path(self):
        self.reject(str(self.repo), state=self.repo / "state")

    def test_resolved_onedrive_path(self):
        self.reject(str(self.root), state=self.base / "local" / ".." / "OneDrive" / "state")
        self.assertFalse(self.root.exists())

    def test_ram_fraction(self):
        self.reject("visible RAM 800.00 MiB", total=800, available=800)

    def test_available_ram(self):
        self.reject("available RAM 671.00 MiB", available=671)

    def test_disk_budget(self):
        self.reject("free disk 895.00 MiB", disk=895)
