"""HTTP contract and actual worker termination for independent hosted visitors."""
from http.cookies import SimpleCookie
import json
from pathlib import Path
import tempfile
import time
import unittest

from .hosted import Hosted


class HostedTest(unittest.TestCase):
    def test_two_visitors_crash_and_expiry(self):
        origin = "https://demo.example"
        with tempfile.TemporaryDirectory() as root:
            site = Hosted(origin, Path(root))

            def call(path, method="GET", cookie="", source=origin):
                response = []
                env = dict(PATH_INFO=path, REQUEST_METHOD=method, HTTP_COOKIE=cookie, HTTP_ORIGIN=source)
                body = b"".join(site(env, lambda status, headers: response.extend([status,dict(headers)])))
                return response[0][:3], response[1], json.loads(body)

            def start():
                code, headers, _ = call("/start", "POST")
                self.assertEqual(code, "200")
                jar = SimpleCookie(headers["Set-Cookie"])
                return "d2session=" + jar["d2session"].value

            def wait(cookie, phase):
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    _, _, state = call("/state", cookie=cookie)
                    if state["phase"] == phase:
                        return state
                    self.assertNotEqual(state["phase"], "error", state["detail"])
                    time.sleep(.05)
                self.fail("Missing phase " + phase)

            try:
                self.assertEqual(call("/start", "POST", source="https://elsewhere.example")[0], "403")
                a, b = start(), start()
                self.assertNotEqual(a, b)
                self.assertEqual(call("/start", "POST")[0], "429")
                old, other = wait(a, "paused"), wait(b, "paused")
                self.assertNotEqual(old["run"], other["run"])
                url = "/edition/" + old["run"] + "/"
                self.assertEqual(len(call(url + "current", cookie=a)[2]["rows"]), 1090)
                self.assertEqual(call(url + "current", cookie=b)[0], "409")
                resume = "/continue/" + old["run"]
                self.assertEqual(call(resume, "POST", b)[0], "409")
                self.assertEqual(call(resume, "POST", a)[0], "200")
                final = wait(a, "complete")
                self.assertEqual(final["result"], dict(rows=2569, duplicates=0, missing=0, extra=0, mismatches=0))
                self.assertEqual(len(call(url + "current", cookie=a)[2]["rows"]), 2569)
                self.assertEqual(len(call(url + old["current"], cookie=a)[2]["rows"]), 1090)
                key = b.split("=",1)[1]
                app, _ = site.sessions.entries[key]
                abandoned = app.db.parent
                site.sessions.entries[key] = app, time.monotonic()-1
                site.sessions.discard_expired()
                self.assertFalse(abandoned.exists())
                self.assertEqual(call("/state", cookie=b)[2]["phase"], "idle")
            finally:
                for app, _ in site.sessions.entries.values():
                    app.close()
