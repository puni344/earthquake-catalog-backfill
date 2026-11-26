"""Fixed-work, end-to-end Windows CLI load benchmark."""
import ctypes
import json
import math
import os
import statistics
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path

from . import acquire, history, ingest, preflight, publish_drill, restart


class MemoryCounters(ctypes.Structure):
    _fields_ = [("size", ctypes.c_uint32), ("faults", ctypes.c_uint32)] + [
        (name, ctypes.c_size_t) for name in ("peak_ws", "ws", "peak_paged", "paged",
                                             "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]


class WorkingSets:
    def __init__(self):
        self.handles = {os.getpid(): -1}  # Current-process pseudo-handle
        self.lock = threading.Lock()
        self.samples = []
        self.measure = ctypes.WinDLL("kernel32", use_last_error=True).K32GetProcessMemoryInfo
        self.measure.argtypes = [ctypes.c_void_p, ctypes.POINTER(MemoryCounters), ctypes.c_uint32]

    @contextmanager
    def track(self, process):
        with self.lock:
            self.handles[process.pid] = int(process._handle)
        try:
            yield
        finally:
            with self.lock:
                del self.handles[process.pid]

    def sample(self, stop):
        while not stop.is_set():
            sizes = {}
            with self.lock:
                for pid, handle in self.handles.items():
                    counters = MemoryCounters()
                    counters.size = ctypes.sizeof(counters)
                    if not self.measure(handle, ctypes.byref(counters), counters.size):
                        raise ctypes.WinError(ctypes.get_last_error())
                    sizes[pid] = counters.ws
            self.samples.append((time.perf_counter_ns(), sizes))
            if sum(sizes.values()) > 672 * preflight.MIB:
                stop.set()
                raise ValueError("sampled project memory exceeded 672 MiB")
            stop.wait(.020)


def emit(label, obj):
    print(label, json.dumps(obj, separators=(",", ":")), flush=True)


def metrics(reads, seconds):
    latencies = sorted((r["finish_ns"] - r["start_ns"]) / 1e6 for r in reads)
    counts = {key: sum(r["status"] == key for r in reads)
              for key in ("success", "error", "timeout", "mismatch")}
    return dict(n=len(reads), **counts, seconds=seconds, reads_per_s=counts["success"]/seconds,
                median_ms=statistics.median(latencies), p95_ms=latencies[math.ceil(.95*len(reads))-1])


def trial(db, level, rep, old, new):
    expected = {o["id"]: o for o in (old, new)}
    ingest.ingest(db, lambda *_: None, lambda *_: None)
    restart.require(history.publish(db, 3) == old["id"], "initial publication mismatch")
    mem = WorkingSets()
    stop = threading.Event()
    marks = {}
    start = threading.Barrier(level+1, action=lambda: marks.update(start=time.perf_counter_ns()), timeout=20)
    switch = threading.Barrier(level+1, timeout=20)
    batches = [[] for _ in range(level)]

    def reader(i):
        warm = publish_drill.observe(db, i, ["current"], expected)
        emit("WARM", warm)
        restart.require(warm["status"] == "success" and warm["id"] == old["id"], "failed warm-up")
        start.wait()
        for seq in range(8):
            restart.require(not stop.is_set(), "trial stopped")
            r = publish_drill.observe(db, i, ["current"], expected, mem.track)
            batches[i].append(r)
            if seq == 0:
                switch.wait()

    with ThreadPoolExecutor(max_workers=level+1) as pool:
        workers = [pool.submit(reader, i) for i in range(level)]
        sampler = None
        try:
            start.wait()
            sampler = pool.submit(mem.sample, stop)
            switch.wait()
            marks["publish"] = time.perf_counter_ns()
            current = history.publish(db, 7)
            marks["committed"] = time.perf_counter_ns()
            restart.require(current == new["id"], "candidate publication mismatch")
            for worker in workers:
                worker.result(timeout=85)
        finally:
            stop.set()
            try:
                if sampler:
                    sampler.result(timeout=5)
            finally:
                emit("MARKS", marks)
                for batch in batches:
                    for r in batch:
                        emit("READ", r)
                emit("WORKING_SET_SAMPLES_ns_pid_bytes", mem.samples)
    reads = [r for batch in batches for r in batch]
    for r in reads:
        if r["status"] == "success" and (
            r["finish_ns"] <= marks["publish"] and r["id"] != old["id"]
            or r["start_ns"] >= marks["committed"] and r["id"] != new["id"]
        ):
            r["status"] = "mismatch"
            emit("WRONG_CURRENT", r)
    seconds = (max(r["finish_ns"] for r in reads)-marks["start"])/1e9
    peak = max(sum(sizes.values()) for _, sizes in mem.samples)/preflight.MIB
    stats = metrics(reads, seconds)
    overlap = sum(r["start_ns"] < marks["committed"] and r["finish_ns"] > marks["publish"] for r in reads)
    old_n, new_n = (sum(r["id"] == o["id"] for r in reads) for o in (old, new))
    emit("TRIAL", dict(level=level, rep=rep, **stats, old=old_n, new=new_n, overlap=overlap,
                       samples=len(mem.samples), sampled_peak_MiB=peak))
    restart.require(stats["success"] == 8*level and min(overlap, old_n, new_n)>0, "trial gate failed")
    return reads, seconds, peak


def run():
    try:
        state = restart.state_directory()
        old, new = publish_drill.oracles()
        for level in (1, 2, 4):
            all_reads, elapsed, peaks = [], 0, []
            for rep in range(1, 4):
                with tempfile.TemporaryDirectory(dir=state, prefix="m07-") as directory:
                    print(f"{acquire.now()} START level={level} rep={rep} state={directory}", flush=True)
                    reads, seconds, peak = trial(Path(directory)/"catalog.sqlite", level, rep, old, new)
                all_reads.extend(reads)
                elapsed += seconds
                peaks.append(peak)
            emit("LEVEL", dict(level=level, **metrics(all_reads, elapsed), sampled_peak_MiB=max(peaks)))
        print("PASS: 4 reader loops highest tested")
    except (OSError, ValueError, RuntimeError, threading.BrokenBarrierError, TimeoutError) as error:
        print("FAIL:", repr(error))
        return 1
    return 0
