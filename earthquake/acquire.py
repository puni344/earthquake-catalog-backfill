"""Freeze independent ComCat responses. The manifest is the completion marker."""
import hashlib
import http.client
import json
import math
import re
import shutil
import sqlite3
from contextlib import closing
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

from . import preflight

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "earthquake" / "fixtures"
ENDPOINT = "https://earthquake.usgs.gov/fdsnws/event/1/query"
START = datetime(2026, 10, 1, tzinfo=timezone.utc)
DAY = timedelta(days=1)
MAX_BODY = 8 * 1024 * 1024


def iso(value):
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def now():
    return iso(datetime.now(timezone.utc))


def windows():
    yield "whole", START, START + 7 * DAY
    for i in range(7):
        yield "daily", START + i * DAY, START + (i + 1) * DAY


def query(role, start, end):
    params = dict(format="geojson", eventtype="earthquake", orderby="time-asc",
                  starttime=iso(start), endtime=iso(end - timedelta(milliseconds=1)))
    return dict(role=role, start=iso(start), end_exclusive=iso(end),
                parameters=params, url=ENDPOINT + "?" + urlencode(params))


def blob(folder, digest):
    if not re.fullmatch("[0-9a-f]{64}", digest):
        raise ValueError(f"invalid SHA-256: {digest!r}")
    return folder / "blobs" / (digest + ".geojson")


def inspect(raw, status, start, end):
    if status == 204 and not raw:
        return 0
    if status != 200:
        raise ValueError(f"unexpected HTTP status {status}")
    doc = json.loads(raw)
    if not isinstance(doc, dict) or not isinstance(doc.get("metadata"), dict):
        raise ValueError("invalid GeoJSON collection metadata")
    features = doc["features"]
    metadata = doc["metadata"]
    if doc["type"] != "FeatureCollection" or not isinstance(features, list):
        raise ValueError("invalid GeoJSON collection")
    declared = metadata.get("count", len(features))
    if metadata.get("status") != 200 or type(declared) is not int or declared != len(features):
        raise ValueError("invalid metadata status or feature count")
    if len(features) >= 20000 or metadata.get("warning") or metadata.get("warnings"):
        raise ValueError("result ceiling reached or server warning present")
    low, high = int(start.timestamp() * 1000), int(end.timestamp() * 1000)
    for feature in features:
        props = feature["properties"]
        if (feature["type"] != "Feature" or not isinstance(feature["id"], str) or not feature["id"]
                or props["type"] != "earthquake" or type(props["time"]) is not int
                or not low <= props["time"] < high or type(props["updated"]) is not int):
            raise ValueError("unexpected feature shape, event type or origin time")
        if props["mag"] is not None and (type(props["mag"]) not in (float, int)
                                         or not math.isfinite(props["mag"])):
            raise ValueError("invalid magnitude")
    return len(features)


def retry_delay(header, number):
    delay = 2 ** number
    if header:
        if header.isdecimal():
            delay = max(delay, int(header))
        else:
            delay = max(delay, parsedate_to_datetime(header).timestamp() - time.time())
    if delay > 60:
        raise ValueError(f"server requests {delay:.0f}s backoff; stopping without another request")
    return delay


def save_body(response, path):
    with path.open("xb") as output:
        while chunk := response.read(65536):
            if output.tell() + len(chunk) > MAX_BODY:
                raise ValueError(f"response exceeds {MAX_BODY}-byte safety cap")
            output.write(chunk)
    expected = response.headers.get("Content-Length")
    if expected is not None and path.stat().st_size != int(expected):
        raise ValueError(f"truncated body: expected {expected}, saved {path.stat().st_size}")


def log_attempt(folder, entry):
    with (folder / "attempts.jsonl").open("a", encoding="utf-8") as log:
        print(json.dumps(entry), file=log)


def fetch(folder, role, start, end):
    entry = query(role, start, end)
    attempts = []
    request = Request(entry["url"], headers={"User-Agent": "D2-catalog-fixture/1",
                                              "Accept-Encoding": "identity"})
    for number in range(1, 4):
        path = folder / f"{role}-{start.date()}-{number}.body"
        attempt = dict(number=number, requested_utc=now(), url=entry["url"])
        attempts.append(attempt)
        log_attempt(folder, attempt)
        retry_after = None
        try:
            try:
                response = urlopen(request, timeout=30)
            except HTTPError as error:
                response = error
            with response:
                status = response.status
                attempt["http_status"] = status
                retry_after = response.headers.get("Retry-After")
                save_body(response, path)
                if status in (408, 429, 500, 502, 503, 504):
                    raise URLError(f"retryable HTTP {status}")
            raw = path.read_bytes()
            count = inspect(raw, status, start, end)
        except (URLError, TimeoutError, ConnectionError, http.client.HTTPException) as error:
            attempt.update(error=str(error), finished_utc=now())
            log_attempt(folder, attempt)
            print(f"attempt {number}: {error}", flush=True)
            if number == 3:
                raise
            delay = retry_delay(retry_after, number)
            attempt["backoff_seconds"] = delay
            time.sleep(delay)
            continue
        except (ValueError, KeyError, TypeError, OSError) as error:
            log_attempt(folder, dict(attempt, error=str(error), finished_utc=now()))
            raise
        attempt["finished_utc"] = now()
        log_attempt(folder, attempt)
        entry.update(acquired_utc=attempt["finished_utc"], http_status=status, size=len(raw),
                     sha256=hashlib.sha256(raw).hexdigest(), features=count, attempts=attempts)
        print(f"{role} {start.date()} | HTTP {status} | {count} features | {len(raw)} bytes | "
              f"{entry['sha256']} | attempts={number}", flush=True)
        return entry, path


def check_response(path, record, role, start, end):
    if any(record[key] != value for key, value in query(role, start, end).items()):
        raise ValueError(f"query metadata mismatch: {role} {start.date()}")
    attempts = record["attempts"]
    if (not attempts or [a["number"] for a in attempts] != list(range(1, len(attempts)+1))
            or len(attempts) > 3 or attempts[-1]["http_status"] != record["http_status"]
            or attempts[-1]["finished_utc"] != record["acquired_utc"]
            or any(a["url"] != record["url"] for a in attempts)):
        raise ValueError("invalid request provenance")
    raw = path.read_bytes()
    if len(raw) != record["size"] or hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise ValueError(f"size or SHA-256 mismatch: {role} {start.date()}")
    try:
        count = inspect(raw, record["http_status"], start, end)
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"{path.name}: {error}") from error
    if count != record["features"]:
        raise ValueError(f"feature count mismatch: {role} {start.date()}")
    return raw


def verified_bodies(folder, records):
    expected = list(windows())
    if len(records) != len(expected):
        raise ValueError(f"expected {len(expected)} responses; got {len(records)}")
    for record, (role, start, end) in zip(records, expected):
        path = blob(folder, record["sha256"])
        raw = check_response(path, record, role, start, end)
        yield path, raw


def validate(folder, records):
    for _ in verified_bodies(folder, records):
        pass


def manifest_records(path):
    manifest = json.loads(path.read_bytes())
    if path.name != "manifest.json" or manifest["schema"] != 1 or manifest["complete"] is not True:
        raise ValueError("expected completed fixture manifest")
    return manifest["responses"]


def seal(folder, records):
    validate(folder, records)
    temp = folder / "manifest.pending"
    with temp.open("w", encoding="utf-8", newline="\n") as out:
        print(json.dumps(dict(schema=1, complete=True, responses=records), indent=2), file=out)
    temp.rename(folder / "manifest.json")


def collect(state, exports, resume=None):
    run_id = resume or (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:12])
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}", run_id):
        raise ValueError(f"invalid acquisition ID: {run_id!r}")
    work = state / run_id
    if resume is None:
        work.mkdir(parents=True, exist_ok=False)
    elif not work.is_dir():
        raise ValueError(f"unknown acquisition: {run_id}")
    print(f"Staging: {work}", flush=True)
    destination = exports / run_id
    manifest = destination / "manifest.json"
    # OS releases the SQLite write lock when the collector process exits.
    with closing(sqlite3.connect(work / "writer.sqlite", timeout=0)) as lock:
        lock.execute("BEGIN IMMEDIATE")
        if resume is None:
            destination.mkdir(parents=True, exist_ok=False)
        if manifest.exists():
            records = manifest_records(manifest)
            validate(destination, records)
            for record, (role, start, _) in zip(records, windows()):
                receipt = json.loads((work / f"{role}-{start.date()}.json").read_bytes())
                if receipt["acquisition"] != run_id or receipt["response"] != record:
                    raise ValueError(f"completed manifest disagrees with receipt: {role} {start.date()}")
        else:
            (destination / "blobs").mkdir(parents=True, exist_ok=True)
            records = []
            for role, start, end in windows():
                receipt = work / f"{role}-{start.date()}.json"
                if receipt.exists():
                    saved = json.loads(receipt.read_bytes())
                    if saved["acquisition"] != run_id:
                        raise ValueError(f"acquisition mismatch in {receipt.name}")
                    record = saved["response"]
                    generation = saved["generation"]
                    if not re.fullmatch("[0-9a-f]{32}", generation):
                        raise ValueError(f"invalid staging directory in {receipt.name}")
                    path = work / generation / f"{role}-{start.date()}-{len(record['attempts'])}.body"
                    check_response(path, record, role, start, end)
                else:
                    # Unreceipted bytes cannot authenticate a request. Preserve them and refetch.
                    stage = work / uuid4().hex
                    stage.mkdir()
                    record, path = fetch(stage, role, start, end)
                    pending = receipt.with_suffix(".pending")
                    pending.write_text(json.dumps(dict(acquisition=run_id, generation=stage.name,
                                                       response=record)), encoding="utf-8")
                    pending.replace(receipt)
                target = blob(destination, record["sha256"])
                if not target.exists():
                    pending = target.with_suffix(".pending")
                    shutil.copyfile(path, pending)
                    check_response(pending, record, role, start, end)
                    pending.replace(target)
                else:
                    check_response(target, record, role, start, end)
                records.append(record)
            seal(destination, records)
    print(f"COMPLETE: {manifest}")


def run(offline=None, resume=None):
    try:
        if offline is not None:
            records = manifest_records(offline)
            validate(offline.parent, records)
            print(f"OFFLINE PASS: {len(records)} bodies; lengths, SHA-256, queries, "
                  f"shape and counts verified from disk: {offline}")
        else:
            if preflight.run():
                return 1
            _, state, _, _ = preflight.locations()
            collect(state.resolve(), FIXTURES, resume)
    except (sqlite3.Error, OSError, http.client.HTTPException, ValueError, KeyError, TypeError) as error:
        print(f"FAIL acquisition: {error}", flush=True)
        return 1
    return 0
