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

class RetainedResponse(unittest.TestCase):
    def test_crash_after_blob_install(self):
        from earthquake.failure_drill import acquisition_restart
        with tempfile.TemporaryDirectory() as folder:
            acquisition_restart(Path(folder), "orphan-raw")

    def exercise_boundary(self, boundary, fault=None):
        from earthquake.failure_drill import measured_transport, replay_map
        bodies = replay_map()
        first, second, *_ = bodies
        replace = Path.replace
        rename = Path.rename

        def interrupt(source, target):
            if boundary == "before-receipt" and target.suffix == ".json":
                raise InterruptedError(boundary)
            result = replace(source, target)
            if ((boundary == "after-receipt" and target.suffix == ".json")
                    or (boundary == "after-body" and target.suffix == ".geojson")):
                raise InterruptedError(boundary)
            return result

        def interrupt_manifest(source, target):
            if boundary == "after-manifest":
                rename(source, target)
            raise InterruptedError(boundary)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state, exports = root / "state", root / "exports"
            serve, _, _ = measured_transport(bodies)
            with patch.object(acquire, "urlopen", side_effect=serve), patch.object(Path, "replace", interrupt), \
                 patch.object(Path, "rename", interrupt_manifest), self.assertRaises(InterruptedError):
                acquire.collect(state, exports)
            work, = state.iterdir()
            destination = exports / work.name
            receipt = work / "whole-2026-10-01.json"
            if fault in ("same-length", "wrong-body"):
                body, = destination.glob("blobs/*.geojson")
                original = body.read_bytes()
                body.write_bytes(original[:-1] + bytes([original[-1] ^ 1])
                                 if fault == "same-length" else bodies[second])
            if fault in ("foreign-run", "wrong-request"):
                saved = json.loads(receipt.read_bytes())
                if fault == "foreign-run":
                    saved["acquisition"] = "20261001T000000Z-aaaaaaaaaaaa"
                else:
                    saved["response"]["url"] = second
                receipt.write_text(json.dumps(saved))
            if fault == "no-receipt":
                receipt.unlink()

            serve, calls, transferred = measured_transport(bodies)
            with patch.object(acquire, "urlopen", side_effect=serve):
                if fault and fault != "no-receipt":
                    with self.assertRaisesRegex(ValueError, "SHA-256|metadata mismatch|acquisition mismatch") as err:
                        acquire.collect(state, exports, resume=work.name)
                    self.assertFalse((destination / "manifest.json").exists())
                    self.assertFalse(calls)
                    print(f"{fault}: failed closed: {err.exception}")
                    return
                acquire.collect(state, exports, resume=work.name)
            refetch = boundary == "before-receipt" or fault == "no-receipt"
            self.assertEqual(calls[first], int(refetch))
            self.assertEqual(transferred[first], len(bodies[first]) if refetch else 0)
            records = acquire.manifest_records(destination / "manifest.json")
            acquire.validate(destination, records)
            print(f"{boundary} {fault}: verified; whole requests={calls[first]} bytes={transferred[first]}")

    def test_adjacent_boundaries(self):
        for point in ("before-receipt", "after-receipt", "before-manifest", "after-manifest"):
            with self.subTest(point=point):
                self.exercise_boundary(point)

    def test_rejection_or_authenticated_refetch(self):
        for fault in ("same-length", "wrong-body", "foreign-run", "wrong-request", "no-receipt"):
            with self.subTest(fault=fault):
                self.exercise_boundary("after-body", fault)
