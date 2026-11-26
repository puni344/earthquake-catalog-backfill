# Earthquake project state

The 23 November 2026 20:00 IST D1 gate expired without a qualifying captured pair. D2 is active. Retain P1 and S1 against named catalog generations. [Design and evidence](design/DESIGN-DOC.md).

[MEASURED – 25 November 2026] Windows and Docker checks, one timestamped daily snapshot, ordinary detail and superseded-product response saved. Capture command from workspace root: `python earthquake/scripts/capture_usgs.py`. Optional bounded sampling: `python earthquake/scripts/capture_usgs.py --minutes 30` (one process, five-minute interval, 128 MiB cap). No ongoing collector required after fallback. [Raw capture log](evidence/quake-capture.txt).

[SOURCE: puni344, 25 November 2026] The three [architecture decisions](adr/README.md) were accepted with validation amendments. The [Turn 4 plan](D2-Turn-4-Milestone-Plan.md) was accepted for implementation one milestone at a time.

M00 establishes the documentation skeleton and CI definition. [MEASURED – 26 November 2026, local Windows checkout] `make docs-check` passed. Disposable copies with a broken link, missing validation heading and omitted ADR index entry each failed with a file-specific diagnostic. Commands and exit codes are in the [M00 transcript](evidence/M00-docs.txt). Hosted CI is **NOT RUN**. M01 through M09, including live agreement, frozen restart, publication history and the integrated demo, are **NOT RUN**. Next decision is M00 review.
