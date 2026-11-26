"""M02 faults use disposable copies of real response bytes."""
import json
import shutil
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from earthquake import acquire


class AcquisitionFaults(unittest.TestCase):
    def test_interrupted_read_never_exports(self):
        raw = next((acquire.REPO / "docs/evidence/usgs").glob("*.geojson")).read_bytes()

        class Interrupted(BytesIO):
            status = 200
            headers = {}

            def read(self, size):
                if self.tell():
                    raise ConnectionResetError("injected disconnect")
                return super().read(512)

        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            with patch.object(acquire, "urlopen", side_effect=lambda *a, **k: Interrupted(raw)), \
                 patch.object(acquire.time, "sleep"):
                with self.assertRaisesRegex(OSError, "injected disconnect"):
                    acquire.collect(base / "state", base / "export")
            self.assertFalse(list(base.rglob("manifest.json")))
            attempts = list(base.rglob("*.body"))
            self.assertEqual(len(attempts), 3)
            self.assertTrue(all(p.read_bytes() == raw[:512] for p in attempts))

    def test_damaged_body_blocks_seal(self):
        source = acquire.FIXTURES / "20261126T064859Z-1bf43bf1e07e" / "manifest.json"
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "fixture"
            shutil.copytree(source.parent, copy)
            manifest = copy / "manifest.json"
            records = json.loads(manifest.read_text())["responses"]
            manifest.unlink()
            body = acquire.blob(copy, records[0]["sha256"])
            data = bytearray(body.read_bytes())
            data[-1] ^= 1
            body.write_bytes(data)
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                acquire.seal(copy, records)
            self.assertFalse(manifest.exists())
