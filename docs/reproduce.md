# Reproduce the crash demo

## Linux and macOS

Clone the repository, enter its root, and run `make verify`. Use Python 3.11 and GNU Make; the Python dependencies are all in the standard library. Make invokes `python3` on these systems. With only Python installed, run `python3 -m earthquake.verify`. To select another interpreter explicitly use `make verify PYTHON=/path/to/python3.11`. The verifier creates a private temporary directory, terminates the paused worker with SIGTERM, inspects the same database after restart, then removes it. The Windows-specific machine preflight and working-set benchmark remain Windows drills.

## Docker

Use a Linux-container Docker engine. Build once from the repository root (the first build downloads the Python base image), then run offline:

```sh
docker build -t d2-verify .
docker run --rm --network none d2-verify
```

The image runs the same Python verifier as a non-root user. Each run uses a new temporary SQLite database. No volume, port, cloud credential or frontend build is needed. Exit zero requires both publication lookups and all verification phases to pass.

## Windows laptop

Use Windows 11 x64 with PowerShell, Git for Windows, native 64-bit CPython **3.10.11** on PATH with its bundled SQLite **3.40.1**, and GNU Make **4.4.1**. The demo uses Python's standard library. Allow a writable fixed local volume under `%LOCALAPPDATA%\D2EarthquakeCatalog\state` outside the checkout and OneDrive, 896 MiB free there and 672 MiB available RAM within 75% of visible RAM. [Resource budget and checks](evidence/M01-preflight.txt)

One-time setup on a Windows machine with App Installer (WinGet): install Git for Windows and the 64-bit Python 3.10.11 installer with **Add python.exe to PATH** selected if missing. Install GNU Make for the current user with the command below, then open a new PowerShell from the Start menu. These free prerequisites may require internet during setup. The demo itself runs offline. [Python installer](https://www.python.org/downloads/release/python-31011/) · [Git for Windows](https://gitforwindows.org/)

```powershell
winget install --id ezwinports.make --exact --version 4.4.1 --source winget --scope user --accept-package-agreements --accept-source-agreements --disable-interactivity
```

Clone this repository with `git clone https://github.com/puni344/earthquake-catalog-backfill.git`, enter it with `cd earthquake-catalog-backfill`, then check prerequisites and run:

```powershell
git --version
(Get-Command make).Source
make --version
python -c "import sys, sqlite3; print(sys.executable, sys.version, sqlite3.sqlite_version)"
make verify
$LASTEXITCODE
```

Look for **Live acquisition agreement: PASS**, **Frozen restart correctness: PASS**, **M08 PASS** and exit **0**. Make calls the direct entry point `python -m earthquake.verify`. Each invocation creates a fresh disposable database. Find the `paused-before` worker event, the three surviving checkpoints, zero October 4 rows and the resumed worker's skips. The `WITNESS` lines identify completed current reads during the outage and after commit. The final `BY-ID` lines show the returned counts and digests. [Integrated transcript](evidence/quake-verify.txt)

### Read published catalogs

The integrated verifier removes its disposable database when it exits. For a live walkthrough, run the following from the checkout root in a new PowerShell after installing the prerequisites above. The history drill creates a separate database under local state and prints its path. The final commands show the actual number of returned rows without printing thousands of events.

```powershell
$demo = make verify
if ($LASTEXITCODE) { throw 'Integrated demo failed' }
$demo | Select-String 'paused-before|Surviving checkpoints|WITNESS|Current reader outcomes|agreement:|correctness:|M08 PASS'

$historyRun = python -m earthquake.verify --drill history
if ($LASTEXITCODE) { throw 'History drill failed' }
$db = ($historyRun | Select-String 'history database=(.+) fixture=').Matches[0].Groups[1].Value
$publications = python -m earthquake.history --db $db list | ConvertFrom-Json
$publications | Select-Object id,start,end_exclusive,count
$current = python -m earthquake.history --db $db current | ConvertFrom-Json
$older = python -m earthquake.history --db $db get $publications[0].id | ConvertFrom-Json
$current,$older | Select-Object id,@{Name='ReturnedRows';Expression={$_.rows.Count}}
```

Listing returns metadata in first-publication order. Current and named reads return JSON containing the ID, half-open UTC coverage, source hashes and event rows. An empty catalog lists as `[]`. Reading current before the first publication or requesting an unknown ID writes a diagnostic to stderr and exits 2.

[MEASURED – M05, 26 November 2026] The 1–3 October extract contained 1,090 rows. Extending coverage through 7 October yielded 2,569. Looking up the shorter publication afterward reproduced its original rows. [IDs, commands and returned-row digests](evidence/M05-history.txt)
### Local Windows dashboard

Run `python -m earthquake.dashboard`, open [the local screen](http://127.0.0.1:8765), then use **Run crash demo**, **Query current**, and **Continue recovery**. An orderly shutdown with Ctrl+C removes the temporary database. [Free hosted deployment configuration](../render.yaml)
