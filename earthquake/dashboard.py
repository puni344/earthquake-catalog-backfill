"""Loopback presentation of the D2 worker crash using a disposable, retained-for-viewing database."""
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event, RLock, Thread
from urllib.parse import urlsplit
from uuid import uuid4

from . import acquire, history, ingest, publish_drill, reconcile, restart

ADDRESS = ("127.0.0.1", 8765)
ASSETS = Path(__file__).with_name("dashboard_assets")


class Presentation:
    def __init__(self, root):
        self.root = root
        self.lock = RLock()
        self.release = Event()
        self.cancel = Event()
        self.folder = self.thread = None
        self.days = [start.date().isoformat() for role, start, end in acquire.windows() if role == "daily"]
        self.state = self.initial("")

    def initial(self, run):
        return dict(run=run, phase="idle", days={d: "Pending" for d in self.days},
                    current=None, editions=[], result=None, detail="Ready to run")

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError("A run is already active")
            if self.folder:
                self.folder.cleanup()
            self.folder = TemporaryDirectory(dir=self.root, prefix="presentation-")
            self.db = Path(self.folder.name) / "catalog.sqlite"
            self.state = self.initial(uuid4().hex)
            self.state.update(phase="running", detail="Checking the frozen fixture")
            self.release.clear()
            self.cancel.clear()
            self.thread = Thread(target=self.work)
            self.thread.start()

    def resume(self, run):
        with self.lock:
            if self.state["phase"] != "paused" or self.state["run"] != run:
                raise ValueError("This run is not waiting for recovery")
            self.state.update(phase="recovering", detail="Resuming the same backfill")
            self.release.set()

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))

    def edition(self, run, key):
        with self.lock:
            if run != self.state["run"] or not self.state["current"]:
                raise ValueError("Select an edition from the active run")
            return history.read(self.db, "current" if key == "current" else "get", key)

    def publish(self, days, oracle):
        key = history.publish(self.db, days)
        self.verify_edition("current", key, oracle)
        with self.lock:
            self.state.update(current=key, editions=history.read(self.db, "list"))
        return key

    def verify_edition(self, action, key, oracle):
        doc = history.read(self.db, action, key)
        restart.require(key == doc["id"] == oracle["id"] and
                        publish_drill.check(doc, {key: oracle})["status"] == "success",
                        "Reader rows disagree with the scoped reference")

    def work(self):
        try:
            files = reconcile.load_fixture()
            restart.require(reconcile.compare(files)["agreement"], "Frozen acquisition paths disagree")
            old, new = publish_drill.oracles()
            def progress(event, day):
                if event == "ack":
                    with self.lock:
                        self.state["days"][day] = "Committed"
            ingest.ingest(self.db, progress, lambda *_: None, through_day=self.days[2])
            original = restart.snapshot(self.db)
            previous = self.publish(3, old)
            events, code = restart.worker_run(self.db, "before")
            marks, rows = restart.snapshot(self.db)
            target = restart.TARGET
            restart.require(events[-1] == ("paused-before", target) and code != 0
                            and (marks, rows) == original and [m[1] for m in marks] == self.days[:3],
                            "Pre-commit termination or surviving checkpoints differ")
            count = Counter(r[1] for r in rows)[target]
            restart.require(count == 0, "Target rows survived")
            self.verify_edition("current", previous, old)
            with self.lock:
                self.state["days"][target] = "Rolled back"
                self.state.update(phase="paused", detail=f"Worker terminated before commit · {len(marks)} checkpoints survived · {count} target rows")
            self.release.wait()
            if self.cancel.is_set():
                return
            resumed, _ = restart.worker_run(self.db)
            skipped = restart.days_for(resumed, "skip")
            attempted = restart.days_for(resumed, "attempt")
            restart.require(skipped == self.days[:3] and attempted == self.days[3:]
                            and restart.days_for(resumed, "ack") == attempted, "Unexpected restart progress")
            marks, rows = restart.snapshot(self.db)
            records = acquire.manifest_records(reconcile.MANIFEST)[1:]
            keys = [(reconcile.fixture_digest(), r["start"][:10], r["sha256"]) for r in records]
            restart.require(marks == keys and rows[:len(original[1])] == original[1], "Checkpoint or prior row mismatch")
            result = restart.verify_recovered(reconcile.reference_rows(*files[0]), rows, keys)
            current = self.publish(7, new)
            for key, oracle in ((previous, old), (current, new)):
                self.verify_edition("get", key, oracle)
            replayed = set(attempted) & set(restart.days_for(events, "attempt"))
            with self.lock:
                self.state["days"].update({d: "Skipped" for d in skipped})
                self.state["days"].update({d: "Replayed" if d in replayed else "Committed" for d in attempted})
                self.state.update(phase="complete", detail="Both publication IDs verified",
                                  result=dict(rows=result["counts"]["daily"]["raw"], duplicates=result["counts"]["daily"]["excess"],
                                              missing=len(result["missing"]), extra=len(result["extra"]), mismatches=len(result["mismatches"])))
        except Exception as exc:
            with self.lock:
                self.state.update(phase="error", detail=f"{type(exc).__name__}: {exc}")

    def close(self):
        self.cancel.set()
        self.release.set()
        if self.thread:
            self.thread.join()
        if self.folder:
            self.folder.cleanup()


class Handler(BaseHTTPRequestHandler):
    def request_data(self, method):
        path = urlsplit(self.path).path
        origin = f"http://{ADDRESS[0]}:{ADDRESS[1]}"
        if self.headers.get("Host") != origin[7:]:
            return self.respond(403, {"error": "Use the loopback URL"})
        app = self.server.presentation
        try:
            if method == "POST":
                if self.headers.get("Origin") != origin:
                    return self.respond(403, {"error": "Local dashboard requests only"})
                if path == "/start":
                    app.start()
                elif path.startswith("/continue/"):
                    app.resume(path.split("/")[-1])
                else:
                    return self.respond(404, {"error": "Unknown action"})
                return self.respond(200, app.snapshot())
            if path == "/state":
                return self.respond(200, app.snapshot())
            parts = path.split("/")
            if len(parts) == 4 and parts[1] == "edition":
                return self.respond(200, app.edition(parts[2], parts[3]))
            assets = {"/": ("index.html", "text/html"), "/style.css": ("style.css", "text/css"),
                      "/app.js": ("app.js", "text/javascript")}
            if path in assets:
                name, mime = assets[path]
                return self.respond(200, (ASSETS / name).read_bytes(), mime)
            self.respond(404, {"error": "Unknown page"})
        except ConnectionError:
            return  # The browser closed or cancelled this poll.
        except (LookupError, ValueError, OSError) as exc:
            self.respond(409, {"error": str(exc)})

    def respond(self, code, data, mime="application/json"):
        raw = data if isinstance(data, bytes) else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.request_data("GET")

    def do_POST(self):
        self.request_data("POST")


def main():
    with ThreadingHTTPServer(ADDRESS, Handler) as server:
        server.presentation = Presentation(restart.state_directory())
        print("Catalog dashboard: http://127.0.0.1:8765", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.presentation.close()


if __name__ == "__main__":
    main()
