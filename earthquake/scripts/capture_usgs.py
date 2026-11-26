import argparse
import hashlib
import json
import math
import os
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
OUT = Path("docs/evidence/usgs")

CAP = 128 * 1024 * 1024
MAX_RESPONSE = 4 * 1024 * 1024
OUT.mkdir(parents=True, exist_ok=True)


def records(raw):
    doc = json.loads(raw)
    if doc["type"] != "FeatureCollection" or doc["metadata"]["status"] != 200:
        raise ValueError("Unexpected feed type or status")
    features = doc["features"]
    if doc["metadata"]["count"] != len(features):
        raise ValueError("Feed count mismatch")
    rows = {}
    for event in features:
        key, props = event["id"], event["properties"]
        if key in rows:
            raise ValueError(f"Duplicate event ID {key}")
        rows[key] = (props["mag"], props["updated"])
    return doc["metadata"]["generated"], rows


def descriptor(path, digest, generated, mag, updated):
    return dict(file=str(path), sha256=digest, feed_generated=generated,
                magnitude=mag, source_updated=updated)


def examine(previous, path, raw):
    generated, rows = records(raw)
    digest = hashlib.sha256(raw).hexdigest()
    print("SNAPSHOT", path, digest, "feed_generated", generated, flush=True)
    if previous:
        old_gen, old_rows, old_path, old_hash = previous
        if generated <= old_gen:
            return previous, None
        for key in sorted(old_rows.keys() & rows.keys()):
            a, ta = old_rows[key]
            b, tb = rows[key]
            if not all(isinstance(x, (float, int)) and math.isfinite(x)
                       for x in (a, b, ta, tb)):
                continue
            if tb > ta and math.floor(a) != math.floor(b):
                return previous, dict(
                    event_id=key,
                    before=descriptor(old_path, old_hash, old_gen, a, ta),
                    after=descriptor(path, digest, generated, b, tb))
    return (generated, rows, path, digest), None


def retry_seconds(value):
    if not value:
        return 0
    if value.isdigit():
        return int(value)
    try:
        return max(0, parsedate_to_datetime(value).timestamp() - time.time())
    except (ValueError, TypeError, OverflowError):
        return 0


def save_pair(pair):
    tmp = OUT / "revision-pair.tmp"
    tmp.write_text(json.dumps(pair, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, OUT / "revision-pair.json")
    print("PAIR FOUND", pair["event_id"], flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=int, default=0, help="Observation window; zero fetches once")
    args = parser.parse_args()
    end = time.time() + max(1, args.minutes * 60)
    used, previous = 0, None
    for path in sorted(OUT.glob("*.geojson")):
        raw = path.read_bytes()
        used += len(raw)
        previous, pair = examine(previous, path, raw)
        if pair:
            save_pair(pair)
            return

    delay = 300
    while time.time() < end and CAP - used >= MAX_RESPONSE:
        try:
            request = Request(URL, headers={"User-Agent": "student-quake-reports/0.1"})
            with urlopen(request, timeout=30) as response:
                raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise SystemExit("STOP: response exceeds configured byte limit")
            records(raw)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            path = OUT / (stamp + ".geojson")
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(raw)
            os.replace(tmp, path)
            used += len(raw)
            previous, pair = examine(previous, path, raw)
            if pair:
                save_pair(pair)
                return
            delay = 300
        except HTTPError as err:
            delay = max(min(delay * 2, 3600), retry_seconds(err.headers.get("Retry-After")))
            print("HTTP ERROR", err.code, "wait_seconds", delay, flush=True)
        except (URLError, TimeoutError, ValueError, KeyError, TypeError) as err:
            delay = min(delay * 2, 3600)
            print("CAPTURE ERROR", repr(err), "wait_seconds", delay, flush=True)
        if args.minutes == 0:
            return
        time.sleep(max(0, min(delay, end - time.time())))
    print("STOP without qualifying pair:",
          "deadline reached" if time.time() >= end else "storage cap reached",
          flush=True)


if __name__ == "__main__":
    main()
