"""Check the checkout's Markdown files, indexes and ADR structure offline."""
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
INDEX = DOCS / "00-index.md"
ADRS = DOCS / "adr"
ADR_INDEX = ADRS / "README.md"
REQUIRED = """
00-index.md adr/README.md design/DESIGN-DOC.md TECH-CHOICES.md failure-register.md
runbooks/README.md postmortems/README.md benchmarks/README.md security/THREAT-MODEL.md
cost/COST.md evidence/README.md DEFENCE.md PROJECT_STATE.md
adr/0001-catalog-structure.md adr/0002-catalog-acquisition.md adr/0003-catalog-storage.md
""".split()
HEADINGS = ("Context", "Decision drivers", "Options considered and comparison matrix",
            "Decision", "Why each alternative was rejected", "Consequences",
            "Revisit when", "Validation plan", "Outcome")
# Repository Markdown uses inline links/images and optional reference definitions.
DEST = r'(?:<([^>]+)>|([^\s)]+(?:\([^()\s]*\)[^\s)]*)*))'
INLINE = re.compile(r'\]\(\s*' + DEST)
REFERENCE = re.compile(r'^ {0,3}\[[^\]]+\]:\s*' + DEST)


def path_name(path):
    return path.relative_to(ROOT).as_posix()


def prose(path):
    fence = ""
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if fence:
            if marker and marker[1].startswith(fence) and not line[marker.end():].strip():
                fence = ""
            continue
        if marker:
            fence = marker[1]
            continue
        yield number, re.sub(r"(`+).*?\1", "", line)


def anchors(path):
    result = set()
    for _, line in prose(path):
        heading = re.match(r"^#{1,6}\s+(.+)", line)
        if heading:
            slug = re.sub(r"[^\w -]", "", heading[1].lower()).strip().replace(" ", "-")
            anchor = slug
            suffix = 0
            while anchor in result:
                suffix += 1
                anchor = f"{slug}-{suffix}"
            result.add(anchor)
    return result


def links(path, errors):
    destinations = []
    for number, line in prose(path):
        for match in (*INLINE.finditer(line), *REFERENCE.finditer(line)):
            value = match[1] or match[2]
            url = urlsplit(value)
            if url.scheme or url.netloc:
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(ROOT) or not target.exists():
                errors.append(f"{path_name(path)}:{number}: broken local link: {value}")
            elif url.fragment and target.suffix.lower() == ".md":
                if unquote(url.fragment) not in anchors(target):
                    errors.append(f"{path_name(path)}:{number}: missing anchor: {value}")
            if url.path:
                destinations.append(target)
    return destinations


def check_index(index, expected, entries, errors):
    counts = Counter(target for target in entries if target.suffix.lower() == ".md")
    for target in sorted(expected - counts.keys()):
        errors.append(f"{path_name(index)}: missing index entry: {target.relative_to(index.parent).as_posix()}")
    for target, count in counts.items():
        if target not in expected or count != 1:
            errors.append(f"{path_name(index)}: unexpected or repeated index entry: {target.name}")


def check_adr(path, errors):
    lines = dict(prose(path)).values()
    for heading in HEADINGS:
        if f"## {heading}" not in lines:
            errors.append(f"{path_name(path)}: missing heading: {heading}")
    metadata = {
        "Status": r"Proposed|Accepted|Rejected|Superseded by ADR-\d{4}",
        "Date / proposed by": r"\d{1,2} \w+ \d{4} / \S.*",
        "Accepted by": r"\S.*",
        "Reversibility": r"(one|two)-way door\b.*",
    }
    for label, pattern in metadata.items():
        fields = [line.split(": ", 1)[1].strip() for line in lines if line.startswith(label + ": ")]
        if len(fields) != 1 or not re.fullmatch(pattern, fields[0]):
            errors.append(f"{path_name(path)}: invalid or missing metadata: {label}")
    if any(line.rstrip() == "Status: Accepted" for line in lines):
        if not any(re.fullmatch(r"Accepted by: .+ on \d{1,2} \w+ \d{4}\s*", line) for line in lines):
            errors.append(f"{path_name(path)}: accepted decision needs approver and date")


def main():
    errors = []
    documents = set(DOCS.rglob("*.md"))
    decisions = {path for path in documents if path.parent == ADRS and path != ADR_INDEX}
    for name in REQUIRED:
        if not (DOCS / name).is_file():
            errors.append(f"docs/{name}: required document missing")
    references = {path: links(path, errors) for path in sorted(documents | {ROOT / "README.md"})}
    check_index(INDEX, documents - decisions - {INDEX}, references.get(INDEX, []), errors)
    check_index(ADR_INDEX, decisions, references.get(ADR_INDEX, []), errors)
    for path in sorted(decisions):
        check_adr(path, errors)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"PASS: README and {len(documents)} docs checked; both indexes current; {len(decisions)} ADRs valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
