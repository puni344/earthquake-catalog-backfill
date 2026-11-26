# Earthquake project state

The 23 November 2026 20:00 IST D1 gate expired without a qualifying captured pair. D2 is active. Retain P1 and S1 against named catalog generations. [Design and evidence](design/DESIGN-DOC.md).

[MEASURED – 25 November 2026] Windows and Docker checks, one timestamped daily snapshot, ordinary detail and superseded-product response saved. Capture command from workspace root: `python earthquake/scripts/capture_usgs.py`. Optional bounded sampling: `python earthquake/scripts/capture_usgs.py --minutes 30` (one process, five-minute interval, 128 MiB cap). No ongoing collector required after fallback. [Raw capture log](evidence/quake-capture.txt).

[SOURCE: puni344, 25 November 2026] The three [architecture decisions](adr/README.md) were accepted with validation amendments. The [Turn 4 plan](D2-Turn-4-Milestone-Plan.md) was accepted for implementation one milestone at a time.

M00 establishes the documentation skeleton and CI definition. [MEASURED – 26 November 2026, local Windows checkout] `make docs-check` passed. Disposable copies with a broken link, missing validation heading and omitted ADR index entry each failed with a file-specific diagnostic. Commands and exit codes are in the [M00 transcript](evidence/M00-docs.txt). Hosted CI is **NOT RUN**. M00 passed local review.

[MEASURED – Windows laptop, 26 November 2026] M01 preflight passed. The native interpreter matched both pins, the resolved state directory passed the configured-root and SQLite checks, and the measured RAM and disk met the design estimates. Seven controlled failures returned nonzero. GNU Make was absent from the fresh shell's PATH. The M00 portable executable was used for the documentation checks. [Raw M01 transcript](evidence/M01-preflight.txt) · [Resource budget](design/DESIGN-DOC.md)

M01 passed local review.

[MEASURED – 26 November 2026, Windows laptop] M02 acquired the predeclared interval in eight independent HTTP requests with zero retries. The whole-week body contained 2,569 features in 1,839,817 bytes. The seven daily bodies contained 2,569 features in 1,842,149 bytes in total. All eight passed offline integrity verification. Disposable interruption and byte-corruption tests blocked completion. [Manifest](../earthquake/fixtures/20261126T064859Z-1bf43bf1e07e/manifest.json) · [M02 transcript](evidence/M02-acquire.txt)

M03 through M09 and hosted CI are **NOT RUN**. The fixture is ready for review. Agreement of event IDs and fields remains untested.
