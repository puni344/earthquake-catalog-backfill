"""Offline comparison of the accepted whole-week and daily acquisition paths."""
import json
from collections import defaultdict
from decimal import Decimal

from . import acquire

MANIFEST = acquire.FIXTURES / "20261126T064859Z-1bf43bf1e07e" / "manifest.json"
DAILY_FIELDS = {"event_time": "time", "source_updated": "updated", "magnitude": "mag"}


def load_fixture():
    records = acquire.manifest_records(MANIFEST)
    files = []
    for index, (path, raw) in enumerate(acquire.verified_bodies(MANIFEST.parent, records)):
        record = records[index]
        print(f"{record['role']} {record['start']} captured={record['acquired_utc']} file={path.name}")
        files.append((path.name, raw))
    return files


def reference_rows(filename, raw):
    # Direct projection of the parent query, independent of the daily field mapping.
    rows = []
    features = json.loads(raw, parse_float=Decimal)["features"] if raw else []
    for index, feature in enumerate(features, 1):
        properties = feature["properties"]
        rows.append((feature["id"], {
            "file": filename, "row": index, "event_time": properties["time"],
            "source_updated": properties["updated"], "magnitude": properties["mag"],
        }))
    return rows


def daily_rows(files):
    rows = []
    for filename, raw in files:
        features = json.loads(raw, parse_float=Decimal)["features"] if raw else []
        for index, feature in enumerate(features, 1):
            observation = {name: feature["properties"][key] for name, key in DAILY_FIELDS.items()}
            observation.update(file=filename, row=index)
            rows.append((feature["id"], observation))
    return rows


def group(rows):
    raw_count = len(rows)
    grouped = defaultdict(list)
    for event_id, observation in rows:
        grouped[event_id].append(observation)
    duplicates = {key: items for key, items in grouped.items() if len(items) > 1}
    counts = dict(raw=raw_count, unique=len(grouped), duplicate_ids=len(duplicates),
                  excess=raw_count - len(grouped))
    return grouped, duplicates, counts


def compare(files):
    reference, ref_duplicates, ref_counts = group(reference_rows(*files[0]))
    daily, daily_duplicates, daily_counts = group(daily_rows(files[1:]))
    missing = {key: reference[key] for key in sorted(reference.keys() - daily.keys())}
    extra = {key: daily[key] for key in sorted(daily.keys() - reference.keys())}
    mismatches = []
    for key in sorted(reference.keys() & daily.keys()):
        for field in ("event_time", "source_updated", "magnitude"):
            if {row[field] for row in reference[key]} != {row[field] for row in daily[key]}:
                mismatches.append(dict(id=key, field=field, reference=reference[key], daily=daily[key]))
    return dict(counts=dict(reference=ref_counts, daily=daily_counts),
                duplicates=dict(reference=ref_duplicates, daily=daily_duplicates),
                missing=missing, extra=extra, mismatches=mismatches,
                agreement=not any((ref_duplicates, daily_duplicates, missing, extra, mismatches)))


def run():
    passed = False
    print(f"Fixture: {MANIFEST}")
    try:
        files = load_fixture()
        print(f"M02 integrity PASS: {len(files)} verified bodies")
        result = compare(files)
        print(json.dumps(result, default=str, sort_keys=True, indent=2))
        print(f"Missing IDs={len(result['missing'])}; extra IDs={len(result['extra'])}; "
              f"field mismatches={len(result['mismatches'])}")
        passed = result["agreement"]
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Fixture error: {error}")
    print("Live acquisition agreement:", "PASS" if passed else "FAIL")
    if not passed:
        print("Extract ineligible for publication")
    print("Frozen restart correctness: NOT RUN (M04)")
    return 0 if passed else 1
