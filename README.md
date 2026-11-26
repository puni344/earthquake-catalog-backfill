# D2 · Restartable earthquake catalog backfill

This checkout also contains D2. Its planned offline demo interrupts a USGS backfill, resumes it, checks every recovered row against an independent reference and retrieves the previous and new publications by ID. These drills are **NOT RUN**.

Today a reviewer with GNU Make and Python 3.10 can run `make docs-check` from the checkout root, inspect the three accepted decisions and compare the saved USGS responses. [D2 documentation](docs/00-index.md) · [Evidence](docs/evidence/README.md)

On the Windows build laptop, run `python -m earthquake.verify --drill preflight` to check the pinned runtime, local SQLite state directory and design budget. [M01 measurements](docs/evidence/M01-preflight.txt)

The frozen USGS catalog covers 1–7 October 2026 UTC. Verify all eight saved bodies offline from the checkout root:

```sh
python -m earthquake.verify --drill acquire --offline earthquake/fixtures/20261126T064859Z-1bf43bf1e07e/manifest.json
```

[Fixture manifest](earthquake/fixtures/20261126T064859Z-1bf43bf1e07e/manifest.json) · [Acquisition evidence](docs/evidence/M02-acquire.txt)

Run `python -m earthquake.verify --drill reconcile` to compare the accepted weekly and daily captures offline. It reports raw multiplicities, missing and extra IDs, and differences in event time, source update time and magnitude. [M03 results](docs/evidence/M03-reconcile.txt)
