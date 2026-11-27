# Earthquake catalog backfill with versioned releases

A worker can die midway through importing the USGS earthquake catalog.  
Analysts need to keep reading the last complete release while the import recovers.  
This demo kills the worker before a SQLite commit, resumes the import, and checks both releases against independent USGS responses. [SOURCE · design](docs/design/DESIGN-DOC.md)

**[Run the weekly crash demo](https://puni344-earthquake-catalog-backfill.onrender.com/)** · [Run the full-year benchmark](https://puni344-earthquake-catalog-backfill.onrender.com/annual) · [Four-minute walkthrough](docs/DEFENCE.md#four-minute-recording-script)

```text
USGS daily responses ──► SQLite rows + checkpoints ───┐
                                                      ├─ compare ─► publish ─► current or by ID
USGS whole-week response ──► independent reference ───┘
```

Run the weekly demo offline from the checkout root on Windows, Linux or macOS:

```sh
make verify
```

Look for **Live acquisition agreement: PASS**, **Frozen restart correctness: PASS** and exit code **0**. [SOURCE · prerequisites, Docker and reader commands](docs/reproduce.md)

## Measured results

| Drill | Result | Measurement and evidence |
|---|---|---|
| Weekly worker crash | October 4 rolled back. Recovery skipped three completed days. Both release IDs still returned their original rows (1,090 and 2,569). | [MEASURED · Windows laptop, 26 Nov 2026, default verifier](docs/evidence/quake-verify.txt) |
| Publisher crash | All 36 concurrent reads returned a complete release across termination and retry. | [MEASURED · Windows laptop, 26 Nov 2026, publish drill](docs/evidence/quake-publish.txt) |
| Reader load | All 168 CLI reads verified at one, two and four concurrent reader loops. | [MEASURED · Windows laptop, 26 Nov 2026, load drill](docs/benchmarks/README.md) |
| Full-year worker crash | Recovery skipped 51 committed windows and replayed one. All 152,183 distinct earthquakes matched the independent reference. | [MEASURED · Windows laptop, 27 Nov 2026, annual benchmark](docs/benchmarks/year-restart.md) |

## Try the crash yourself

In the weekly demo, click **Run crash demo**. When the worker stops, click **Query current** to inspect the shorter release. Click **Continue recovery**, then use **Publication history** to reopen the earlier release. In the annual demo, inspect the surviving checkpoint and row counts before continuing. [SOURCE · walkthrough](docs/DEFENCE.md) · [Weekly dashboard screenshot](docs/evidence/dashboard-history.png)

If you see **Waiting for capacity**, leave the page open. The start button becomes available when a slot opens. To continue a paused run, return to its dashboard in the same browser. [SOURCE · hosted session handling](earthquake/hosted.py)

## Limitations

Publications preserve catalog extracts for declared date ranges. Individual earthquake revision tracking is outside this project's scope. Power-loss durability, multi-host failover and sustained throughput are **NOT RUN**. [Results, workloads and raw evidence](docs/results.md) · [Architecture decisions](docs/adr/README.md) · [Native and container CI](https://github.com/puni344/earthquake-catalog-backfill/actions/workflows/verify.yml)
