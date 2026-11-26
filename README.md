# Earthquake catalog backfill with versioned releases

**[🟢 Run the live crash demo](https://puni344-earthquake-catalog-backfill.onrender.com/)** · [🎬 Four-minute walkthrough](docs/DEFENCE.md#four-minute-recording-script)

Can an analyst still read yesterday’s release while an interrupted backfill recovers? This project answers that question using **one real USGS week, 2,569 distinct earthquakes and seven daily transactions**. A release ID identifies the events and values published for a declared date range. Individual earthquake revision tracking is outside the project’s scope.

| 🟠 Interrupt | 🔵 Inspect | 🟢 Recover |
|---|---|---|
| Click **Run crash demo**. The worker dies before October 4 commits. | Click **Query current**. The October 1–3 release still returns 1,090 events. | Click **Continue recovery**. October 4 replays, the week publishes, and both releases remain readable by ID. |

The free instance may take a minute to wake. Each visitor gets a temporary database. [Dashboard screenshot](docs/evidence/dashboard-history.png)

```text
USGS whole-week response ──► independent reference reader ────────────────┐
Seven daily responses ────► SQLite rows + per-day checkpoints ───────────┤ compare
                                                                        ▼
                                     immutable publications ◄── verified extract
                                        │              │
                                 current pointer     explicit ID
                                        └──── reader CLI ────► hash returned rows
```

### Reproduce it

From the checkout root on Linux, macOS or Windows:

```sh
make verify
```

Expect **Live acquisition agreement: PASS**, **Frozen restart correctness: PASS**, and exit **0**. Prefer containers? Run `docker build -t d2-verify .`, then `docker run --rm --network none d2-verify`. [Platform prerequisites and history commands](docs/reproduce.md) · [Native and container CI](https://github.com/puni344/earthquake-catalog-backfill/actions/workflows/verify.yml)

### What was measured

The recovered week matched the independent reference on event ID, origin time, update time and magnitude. A separate Windows benchmark verified 168 CLI reads across one, two and four concurrent reader loops. These results cover a single writer and a bounded historical week; larger catalogs, sustained throughput and power-loss recovery remain unmeasured. [Results and raw evidence](docs/results.md) · [Architecture decisions](docs/adr/README.md) · [Interview materials](docs/DEFENCE.md)
