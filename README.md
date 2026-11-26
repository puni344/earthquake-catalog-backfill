# D2 · Restartable earthquake catalog backfill

This checkout also contains D2. Its planned offline demo interrupts a USGS backfill, resumes it, checks every recovered row against an independent reference and retrieves the previous and new publications by ID. The integrated crash-and-publication demo is **NOT RUN**.

Today a reviewer with GNU Make and Python 3.10 can run `make docs-check` from the checkout root, inspect the three accepted decisions and compare the saved USGS responses. [D2 documentation](docs/00-index.md) · [Evidence](docs/evidence/README.md)

On the Windows build laptop, run `python -m earthquake.verify --drill preflight` to check the pinned runtime, local SQLite state directory and design budget. [M01 measurements](docs/evidence/M01-preflight.txt)

The frozen USGS catalog covers 1–7 October 2026 UTC. Verify all eight saved bodies offline from the checkout root:

```sh
python -m earthquake.verify --drill acquire --offline earthquake/fixtures/20261126T064859Z-1bf43bf1e07e/manifest.json
```

[Fixture manifest](earthquake/fixtures/20261126T064859Z-1bf43bf1e07e/manifest.json) · [Acquisition evidence](docs/evidence/M02-acquire.txt)

Run `python -m earthquake.verify --drill reconcile` to compare the accepted weekly and daily captures offline. It reports raw multiplicities, missing and extra IDs, and differences in event time, source update time and magnitude. [M03 results](docs/evidence/M03-reconcile.txt)

Run `python -m earthquake.verify --drill restart` on the Windows build laptop to create fresh local databases and kill the ingestion worker on each side of commit. The drill compares recovered rows with the frozen whole-week reference. [Crash observations](docs/evidence/M04-restart.txt) · [Combined reconciliation verdicts](docs/evidence/quake-reconcile.txt)

### Read published catalogs

From the checkout root on the Windows build laptop, the history drill creates a fresh database in local state. These PowerShell commands use the database from that run:

```powershell
python -m earthquake.verify --drill history | Tee-Object -Variable historyRun
$db = ($historyRun | Select-String 'history database=(.+) fixture=').Matches[0].Groups[1].Value
python -m earthquake.history --db $db list
python -m earthquake.history --db $db current
$publications = python -m earthquake.history --db $db list | ConvertFrom-Json
python -m earthquake.history --db $db get $publications[0].id
python -m earthquake.history --db $db get $publications[1].id
```

Listing returns metadata in first-publication order. Current and named reads return JSON containing the ID, half-open UTC coverage, source hashes and event rows. An empty catalog lists as `[]`. Reading current before the first publication or requesting an unknown ID writes a diagnostic to stderr and exits 2.

[MEASURED – M05, 26 November 2026] The 1–3 October extract contained 1,090 rows. Extending coverage through 7 October yielded 2,569. Looking up the shorter publication afterward reproduced its original rows. [IDs, commands and returned-row digests](docs/evidence/M05-history.txt)
