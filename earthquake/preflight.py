"""Check the native Windows runtime, state directory and accepted design budget."""
import ctypes
import os
import platform
import shutil
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

MIB = 2**20
COMPONENTS = (
    ("Downloader and raw staging", 128, 1, 256),
    ("SQLite writer and indexed generations", 256, 1, 384),
    ("Reference checker and concurrent readers", 256, 2, 128),
    ("Logs and evidence", 32, 0.1, 128),
)


def native_windows():
    return os.name == "nt"


def locations():
    import winreg

    raw = os.environ.get("LOCALAPPDATA", "")
    if not Path(raw).is_absolute():
        raise ValueError(f"LOCALAPPDATA must be absolute, got {raw!r}")
    local = Path(raw).resolve()
    roots = {Path(value) for key, value in os.environ.items()
             if key.upper() in {"ONEDRIVE", "ONEDRIVECONSUMER", "ONEDRIVECOMMERCIAL"} and value}
    try:
        accounts = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\OneDrive\Accounts")
    except FileNotFoundError:
        accounts = None
    if accounts is not None:
        with accounts:
            for index in range(winreg.QueryInfoKey(accounts)[0]):
                with winreg.OpenKey(accounts, winreg.EnumKey(accounts, index)) as account:
                    try:
                        folder, _ = winreg.QueryValueEx(account, "UserFolder")
                    except FileNotFoundError:
                        continue
                    if folder:
                        roots.add(Path(os.path.expandvars(folder)))
    return local, local / "D2EarthquakeCatalog" / "state", Path(__file__).resolve().parents[1], roots


def capacity(state):
    # MEMORYSTATUSEX uses two DWORDs followed by seven DWORDLONGs.
    class MemoryStatus(ctypes.Structure):
        _fields_ = [("length", ctypes.c_uint32), ("load", ctypes.c_uint32)] + [
            (key, ctypes.c_uint64) for key in
            ("total", "available", "page_total", "page_available", "virtual_total",
             "virtual_available", "extended_available")
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    volume = ctypes.create_unicode_buffer(32768)
    if not kernel.GetVolumePathNameW(str(state), volume, len(volume)):
        raise ctypes.WinError(ctypes.get_last_error())
    drive_type = kernel.GetDriveTypeW(volume.value)
    if drive_type != 3:  # DRIVE_FIXED
        raise ValueError(f"state volume {volume.value} has drive type {drive_type}; expected fixed disk")
    print(f"State volume: {volume.value} (fixed)")
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    if not kernel.GlobalMemoryStatusEx(ctypes.byref(memory)):
        raise ctypes.WinError(ctypes.get_last_error())
    logical = os.cpu_count()
    if logical is None:
        raise ValueError("logical processor count unavailable")
    return memory.total, memory.available, logical, shutil.disk_usage(state).free


def sqlite_probe(state):
    with TemporaryDirectory(prefix="preflight-", dir=state) as directory:
        db = Path(directory) / "probe.sqlite"
        with closing(sqlite3.connect(db)) as writer:
            writer.execute("CREATE TABLE probe (value TEXT)")
            writer.execute("INSERT INTO probe VALUES (?)", ("D2",))
            writer.commit()
        with closing(sqlite3.connect(db.as_uri() + "?mode=ro", uri=True)) as reader:
            rows = reader.execute("SELECT value FROM probe").fetchall()
        if rows != [("D2",)]:
            raise ValueError(f"SQLite probe returned {rows!r}, expected one D2 row")
    print("SQLite PASS: created, committed, closed, reopened read-only, read D2; probe removed")


def run():
    try:
        python = platform.python_version()
        sqlite = sqlite3.sqlite_version
        print(f"Executable: {sys.executable}\nPython: {python}\nSQLite: {sqlite}")
        if python != "3.10.11":
            raise ValueError(f"Python {python}; ADR-0003 requires 3.10.11")
        if sqlite != "3.40.1":
            raise ValueError(f"SQLite {sqlite}; ADR-0003 requires 3.40.1")
        if not native_windows():
            raise ValueError(f"unsupported OS {sys.platform}; preflight targets native Windows")

        local, candidate, repo, roots = locations()
        state = candidate.resolve()
        print(f"LOCALAPPDATA: {local}\nResolved state: {state}\nRepository: {repo}")
        resolved_roots = sorted({root.resolve() for root in roots})
        print("Configured OneDrive roots:", ", ".join(map(str, resolved_roots)) or "(none found)")
        for forbidden in [repo.resolve(), *resolved_roots]:
            if state.is_relative_to(forbidden):
                raise ValueError(f"state {state} lies inside disallowed root {forbidden}")
        if not state.is_relative_to(local.resolve()):
            raise ValueError(f"resolved state {state} is outside LOCALAPPDATA {local}")
        state.mkdir(parents=True, exist_ok=True)
        total, available, logical, disk = capacity(state)
        print(f"Measured: visible RAM {total/MIB:.2f} MiB; available RAM {available/MIB:.2f} MiB; "
              f"logical processors {logical}; free disk {disk/MIB:.2f} MiB")
        print("Design estimates | RAM MiB | CPU cores | disk MiB")
        for component in COMPONENTS:
            print(" | ".join(map(str, component)))
        ram, cpu, storage = map(sum, zip(*(row[1:] for row in COMPONENTS)))
        print(f"Total estimate | {ram} | {cpu} | {storage}")
        print(f"75% of visible RAM: {0.75*total/MIB:.2f} MiB")
        if ram * MIB * 4 > total * 3:
            raise ValueError(f"visible RAM {total/MIB:.2f} MiB; {ram} MiB exceeds the 75% ceiling")
        if available < ram * MIB:
            raise ValueError(f"available RAM {available/MIB:.2f} MiB; design requires {ram} MiB")
        if disk < storage * MIB:
            raise ValueError(f"free disk {disk/MIB:.2f} MiB on {state}; design requires {storage} MiB")
        sqlite_probe(state)
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as error:
        print(f"FAIL: {error}")
        return 1
    print("PASS: preflight")
    return 0
