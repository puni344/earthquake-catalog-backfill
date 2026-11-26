# D2 · Restartable earthquake catalog backfill

This checkout also contains D2. Its planned offline demo interrupts a USGS backfill, resumes it, checks every recovered row against an independent reference and retrieves the previous and new publications by ID. These drills are **NOT RUN**.

Today a reviewer with GNU Make and Python 3.10 can run `make docs-check` from the checkout root, inspect the three accepted decisions and compare the saved USGS responses. [D2 documentation](docs/00-index.md) · [Evidence](docs/evidence/README.md)

On the Windows build laptop, run `python -m earthquake.verify --drill preflight` to check the pinned runtime, local SQLite state directory and design budget. [M01 measurements](docs/evidence/M01-preflight.txt)
