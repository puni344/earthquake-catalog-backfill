"""Public WSGI adapter. Each browser owns its own disposable Presentation."""
from collections import deque
from http.cookies import SimpleCookie
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time

from .dashboard import ASSETS, Presentation


class CapacityError(Exception):
    pass


class Sessions:
    def __init__(self, root, ttl=600, limit=2):
        self.root = root
        self.ttl = ttl
        self.limit = limit
        self.entries = {}
        self.starts = deque()
        self.lock = threading.RLock()

    def discard_expired(self):
        with self.lock:
            now = time.monotonic()
            for key, (app, deadline) in list(self.entries.items()):
                if now >= deadline:
                    app.close()
                    del self.entries[key]

    def start(self, key):
        with self.lock:
            now = time.monotonic()
            while self.starts and self.starts[0] <= now - 60:
                self.starts.popleft()
            if len(self.starts) >= 10:
                raise CapacityError("Please retry in one minute.")
            active = sum(app.thread.is_alive() for app, _ in self.entries.values())
            if active >= self.limit and key not in self.entries:
                raise CapacityError("Both demo slots are in use. Try again shortly.")
            if key in self.entries:
                app = self.entries[key][0]
                if active >= self.limit and not app.thread.is_alive():
                    raise CapacityError("Both demo slots are in use. Try again shortly.")
            else:
                if len(self.entries) >= 8:
                    retired = next(k for k, (p, _) in self.entries.items() if not p.thread.is_alive())
                    self.entries.pop(retired)[0].close()
                key = secrets.token_urlsafe(32)
                app = Presentation(self.root)
            app.start()
            self.starts.append(now)
            self.entries[key] = app, now + self.ttl
            return key, app.snapshot()

    def dispatch(self, key, method, path):
        with self.lock:
            if method == "POST" and path == "/start":
                return self.start(key)
            app = self.entries.get(key, (None,))[0]
            if method == "GET" and path == "/state":
                if app:
                    return None, app.snapshot()
                state = Presentation(self.root).snapshot()
                if key:
                    state["detail"] = "Session expired. Start a fresh demo."
                return None, state
            if not app:
                raise ValueError("Session expired. Start a fresh demo.")
            parts = path.strip("/").split("/")
            if method == "POST" and len(parts) == 2 and parts[0] == "continue":
                app.resume(parts[1])
                return None, app.snapshot()
            if method == "GET" and len(parts) == 3 and parts[0] == "edition":
                return None, app.edition(parts[1], parts[2])
            raise LookupError("Unknown route")


class Hosted:
    def __init__(self, origin, root):
        self.origin = origin
        self.sessions = Sessions(root)
        self.assets = {url: ((ASSETS / name).read_bytes(), mime) for url, name, mime in [
            ("/", "index.html", "text/html"), ("/app.js", "app.js", "text/javascript"),
            ("/style.css", "style.css", "text/css")]}
        html, mime = self.assets["/"]
        self.assets["/"] = html.replace(b"Local session", b"Live session"), mime

    def __call__(self, env, respond):
        method, path = env["REQUEST_METHOD"], env["PATH_INFO"]
        headers = [("Cache-Control", "no-store"), ("X-Content-Type-Options", "nosniff"),
                   ("Referrer-Policy", "no-referrer"), ("Content-Security-Policy",
                    "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")]
        status, mime = "200 OK", "application/json"
        try:
            if method == "GET" and path == "/health":
                data = {"ok": True}
            elif method == "GET" and path in self.assets:
                data, mime = self.assets[path]
            elif method == "POST" and env.get("HTTP_ORIGIN") != self.origin:
                status, data = "403 Forbidden", {"error": "Use the public dashboard to start a run"}
            else:
                cookie = SimpleCookie()
                cookie.load(env.get("HTTP_COOKIE", ""))
                key = cookie["d2session"].value if "d2session" in cookie else None
                issued, data = self.sessions.dispatch(key, method, path)
                if issued:
                    headers.append(("Set-Cookie", f"d2session={issued}; Path=/; Secure; HttpOnly; SameSite=Strict"))
        except CapacityError as exc:
            status, data = "429 Too Many Requests", {"error": str(exc)}
        except ValueError as exc:
            status, data = "409 Conflict", {"error": str(exc)}
        except LookupError:
            status, data = "404 Not Found", {"error": "Unknown publication or route"}
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
        respond(status, headers + [("Content-Type", mime + "; charset=utf-8"), ("Content-Length", str(len(body)))])
        return [body]


def main():
    from waitress import serve
    origin = os.environ["RENDER_EXTERNAL_URL"].rstrip("/")
    with tempfile.TemporaryDirectory(prefix="catalog-host-") as root:
        site = Hosted(origin, Path(root))
        stop = threading.Event()

        def reap():
            while not stop.wait(5):
                site.sessions.discard_expired()

        thread = threading.Thread(target=reap, daemon=True)
        thread.start()
        try:
            serve(site, host="0.0.0.0", port=int(os.environ.get("PORT", "10000")),
                  threads=4, connection_limit=64, max_request_body_size=1024)
        finally:
            stop.set()
            thread.join()
            for app, _ in site.sessions.entries.values():
                app.close()


if __name__ == "__main__":
    main()
