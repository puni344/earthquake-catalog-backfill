"""Check local evidence citations for tagged measurements in public-facing Markdown."""
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

from earthquake.scripts.check_docs import DEST, ROOT, prose

TAG = re.compile(r"\[MEASURED\b")
LINK = re.compile(r"\[[^\[\]\n]*\]\(\s*" + DEST)
NEW_BLOCK = re.compile(r"^\s*(?:\||#{1,6}\s|[-*+]\s|\d+[.)]\s|>)")


def claims(document):
    """Yield each tag and its following prose up to the next claim or block."""
    start = None
    parts = []
    previous = 0
    for number, line in prose(document):
        if not line.strip() or number != previous + 1 or NEW_BLOCK.match(line):
            if parts:
                yield start, " ".join(parts)
            parts = []
            start = None
        previous = number
        pos = 0
        for tag in TAG.finditer(line):
            if start is not None:
                parts.append(line[pos:tag.start()])
                yield start, " ".join(parts)
            parts = []
            start = number
            pos = tag.start()
        if start is not None:
            parts.append(line[pos:])
    if parts:
        yield start, " ".join(parts)


def has_evidence(text, document, roots):
    for link in LINK.finditer(text):
        url = urlsplit(link[1] or link[2])
        if url.scheme or url.netloc or not url.path:
            continue
        relative = Path(unquote(url.path))
        if relative.is_absolute() or relative.drive or relative.root:
            continue
        target = (document.parent / relative).resolve()
        if target.is_file() and any(target.is_relative_to(root) for root in roots):
            return True
    return False


def check(root):
    docs = root / "docs"
    roots = (docs / "evidence", docs / "benchmarks")
    errors = []
    count = 0
    for document in [root / "README.md", *sorted(docs.glob("*.md"))]:
        for number, text in claims(document):
            count += 1
            if not has_evidence(text, document, roots):
                errors.append(f"{document.relative_to(root).as_posix()}:{number}: "
                              "measurement needs a link to a file in docs/evidence/ or docs/benchmarks/")
    return count, errors


if __name__ == "__main__":
    count, errors = check(ROOT)
    print("\n".join(errors) if errors else f"PASS: {count} measured claims link to local evidence")
    sys.exit(bool(errors))
