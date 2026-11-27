"""Exercise the evidence contract against disposable Markdown fixtures."""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from earthquake.scripts.check_evidence import check


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.docs = self.root / "docs"
        self.readme = self.root / "README.md"
        self.readme.write_text("", encoding="utf8")
        for folder in ("benchmarks", "evidence"):
            directory = self.docs / folder
            directory.mkdir(parents=True)
            (directory / "run.txt").write_text("observed", encoding="utf8")

    def test_linked_tag_and_wrapped_claim(self):
        self.readme.write_text("- [Measured results and limits](docs/results.md)\n| [MEASURED yesterday](docs/benchmarks/run.txt) |", encoding="utf8")
        (self.docs / "results.md").write_text(
            "[MEASURED today] completed\n[transcript](evidence/run.txt)\n", encoding="utf8")
        self.assertEqual(check(self.root), (2, []))

    def test_every_unsupported_claim_has_a_location(self):
        self.readme.write_text(
            "[MEASURED A] missing [log](docs/evidence/missing)\n"
            "| [MEASURED B] directory [folder](docs/evidence/) |\n"
            "| [MEASURED C] external [log](https://example.org/docs/evidence/run.txt) |\n"
            "[MEASURED D] outside [file](docs/evidence/../../README.md) [MEASURED E](docs/evidence/run.txt)\n"
            "\n```\n[MEASURED example]\n```\n", encoding="utf8")
        count, errors = check(self.root)
        self.assertEqual(count, 5)
        self.assertEqual([s.split(": ")[0] for s in errors],
                         [f"README.md:{line}" for line in (1, 2, 3, 4)])

    def test_nested_claims_include_runbooks_and_postmortems(self):
        for folder in ("adr", "benchmarks", "runbooks/nested", "postmortems", "evidence"):
            directory = self.docs / folder
            directory.mkdir(parents=True, exist_ok=True)
            (directory / "example.md").write_text("[MEASURED today] unsupported", encoding="utf8")
        count, errors = check(self.root)
        self.assertEqual(count, 5)
        self.assertEqual(len(errors), 5)
        self.assertIn("docs/runbooks/nested/example.md:1:", "\n".join(errors))
