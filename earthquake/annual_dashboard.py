"""Hosted annual benchmark with an operator-controlled recovery boundary."""
import hashlib
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from threading import Event, RLock, Thread
from urllib.request import Request, urlopen
from uuid import uuid4
from zipfile import ZipFile

from . import year, year_restart

URL = "https://github.com/puni344/earthquake-catalog-backfill/releases/download/comcat-2024-v1/comcat-2024.zip"
SHA256 = "1ab2db61a9b851cd63de14113468143368f4575cc7374fbcad33678509cb8a51"


def install(root, archive):
    folder = root / "comcat-2024"
    if hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        raise ValueError("Annual release archive checksum mismatch")
    with TemporaryDirectory(dir=root) as tmp, ZipFile(archive) as zipped:
        dest = Path(tmp) / "fixture"
        dest.mkdir()
        names = ["manifest.json"] + [year.name(role, start) + ".body" for role, start, _ in year.plan()]
        if sorted(names) != sorted(zipped.namelist()):
            raise ValueError("Unexpected annual archive members")
        for name in names:
            with zipped.open(name) as src, (dest / name).open("xb") as out:
                shutil.copyfileobj(src, out)
        dest.rename(folder)
    return folder


def fixture(root):
    folder = root / "comcat-2024"
    if folder.exists():
        return folder
    with TemporaryDirectory(dir=root) as tmp:
        archive = Path(tmp) / "fixture.zip"
        with urlopen(Request(URL, headers={"User-Agent": "D2-catalog-demo"}), timeout=45) as src:
            with archive.open("wb") as out:
                for chunk in iter(lambda: src.read(262144), b""):
                    out.write(chunk)
                    if out.tell() > 26208986:
                        raise ValueError("Oversized annual archive")
        return install(root, archive)


class Annual:
    def __init__(self, root):
        self.root = root
        self.lock = RLock()
        self.gate = Event()
        self.thread = None
        self.state = dict(phase="idle", run=None, detail="Ready to ingest the frozen 2024 catalog.")

    def snapshot(self):
        with self.lock:
            return self.state.copy()

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError("Annual benchmark already running")
            self.gate.clear()
            self.cancelled = False
            self.state = dict(run=uuid4().hex, phase="running", detail="Preparing the frozen fixture and ingesting UTC windows.")
            self.thread = Thread(target=self.work, daemon=True)
            self.thread.start()

    def update(self, **values):
        with self.lock:
            self.state.update(values)

    def interrupted(self, observation):
        self.update(phase="paused", detail="Worker terminated before commit. A fresh SQLite connection inspected the database.", observation=observation)
        self.gate.wait()
        if self.cancelled:
            raise ValueError("Session expired during interruption")

    def resume(self, run):
        with self.lock:
            if run != self.state["run"] or self.state["phase"] != "paused":
                raise ValueError("This run is not paused")
            self.update(phase="recovering", detail="Resuming the same database and checking all recovered rows against independent responses.")
            self.gate.set()

    def work(self):
        try:
            result, comparison = year_restart.benchmark(fixture(self.root), self.root, self.interrupted)
            self.update(phase="complete", detail="Independent reference comparison passed.", result=result, comparison=comparison)
        except Exception as exc:
            self.update(phase="error", detail=str(exc))

    def close(self):
        self.cancelled = True
        self.gate.set()
        if self.thread:
            self.thread.join()
