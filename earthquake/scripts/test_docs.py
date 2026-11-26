"""Exercise the real Makefile on disposable copies of the checkout documents."""
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[2]
    with tempfile.TemporaryDirectory() as directory:
        copy = Path(directory)
        # Preserve relative link targets, including files from the companion project.
        tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=root)
        for name in tracked.decode("utf-8").split("\0"):
            source = root / name
            if name and source.is_file() and not name.startswith("docs/"):
                target = copy / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        shutil.copytree(root / "docs", copy / "docs")
        for name in ("README.md", "Makefile", "earthquake/scripts/check_docs.py"):
            target = copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / name, target)
        adr = "docs/adr/0001-catalog-structure.md"
        cases = [
            ("docs/PROJECT_STATE.md", lambda s: s + "\n[broken](missing-m00.md)\n",
             "missing-m00.md"),
            (adr, lambda s: s.replace("## Validation plan", "## Removed"),
             "missing heading: Validation plan"),
            ("docs/adr/README.md", lambda s: "\n".join(
                line for line in s.splitlines() if "0001-catalog-structure.md" not in line
            ), "missing index entry: 0001-catalog-structure.md"),
        ]
        for name, mutate, reason in cases:
            file = copy / name
            original = file.read_bytes()
            file.write_text(mutate(file.read_text(encoding="utf-8")), encoding="utf-8")
            result = subprocess.run(["make", "docs-check"], cwd=copy,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding="utf-8", errors="replace")
            output = result.stdout
            print(f"\nDisposable copy: {name}\n$ make docs-check\n{output}exit={result.returncode}")
            if not result.returncode or not any(
                name in line and reason in line for line in output.splitlines()
            ):
                raise SystemExit(f"Expected diagnostic for {name}: {reason}")
            file.write_bytes(original)
        print("PASS: all three defects rejected for their expected reason")


if __name__ == "__main__":
    main()
