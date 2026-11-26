# Earthquake project state

The 23 November 2026 20:00 IST D1 gate expired without a qualifying captured pair. D2 is active. Retain P1 and S1 against named catalog generations. [Design and evidence](design/DESIGN-DOC.md).

[MEASURED – 25 November 2026] Windows and Docker checks, one timestamped daily snapshot, ordinary detail and superseded-product response saved. Capture command from workspace root: `python earthquake/scripts/capture_usgs.py`. Optional bounded sampling: `python earthquake/scripts/capture_usgs.py --minutes 30` (one process, five-minute interval, 128 MiB cap). No ongoing collector required after fallback. [Raw capture log](evidence/quake-capture.txt).

[SOURCE: puni344, 25 November 2026] The three [architecture decisions](adr/README.md) were accepted with validation amendments. The [Turn 4 plan](D2-Turn-4-Milestone-Plan.md) was accepted for implementation one milestone at a time.

M00 establishes the documentation skeleton and CI definition. [MEASURED – 26 November 2026, local Windows checkout] `make docs-check` passed. Disposable copies with a broken link, missing validation heading and omitted ADR index entry each failed with a file-specific diagnostic. Commands and exit codes are in the [M00 transcript](evidence/M00-docs.txt). Hosted CI is **NOT RUN**. M00 passed local review.

[MEASURED – Windows laptop, 26 November 2026] M01 preflight passed. The native interpreter matched both pins, the resolved state directory passed the configured-root and SQLite checks, and the measured RAM and disk met the design estimates. Seven controlled failures returned nonzero. GNU Make was absent from the fresh shell's PATH. The M00 portable executable was used for the documentation checks. [Raw M01 transcript](evidence/M01-preflight.txt) · [Resource budget](design/DESIGN-DOC.md)

M01 passed local review.

[MEASURED – 26 November 2026, Windows laptop] M02 acquired the predeclared interval in eight independent HTTP requests with zero retries. The whole-week body contained 2,569 features in 1,839,817 bytes. The seven daily bodies contained 2,569 features in 1,842,149 bytes in total. All eight passed offline integrity verification. Disposable interruption and byte-corruption tests blocked completion. [Manifest](../earthquake/fixtures/20261126T064859Z-1bf43bf1e07e/manifest.json) · [M02 transcript](evidence/M02-acquire.txt)

[MEASURED – 26 November 2026, M03 offline drill] Live acquisition agreement **PASS** for the accepted M02 capture. Each side contained 2,569 raw rows and 2,569 unique IDs. Both had zero duplicate IDs and zero excess rows. No missing IDs, extra IDs or projected field mismatches were found. The equal-count fault preserved 2,569 daily rows and produced one missing ID and one duplicate ID. [Reconciliation transcript](evidence/M03-reconcile.txt)

[MEASURED – M04, 26 November 2026, Windows laptop] Frozen restart correctness **PASS**. On 4 October, the before-commit worker kill left zero target rows and no checkpoint. The after-commit kill left 383 target rows and its checkpoint. Independent reference comparison found 2,569 unique IDs and no differences in either recovered extract. Both completed reruns skipped all seven windows and preserved every row and checkpoint. [Crash transcript](evidence/M04-restart.txt) · [Combined verdicts](evidence/quake-reconcile.txt)

[MEASURED – M05, 26 November 2026, Windows laptop] History drill **PASS**. Both publications were complete for their declared UTC scopes. Independent reference checks passed for current and explicit IDs. After the 2,569-row publication became current, the older ID still returned its original 1,090 rows and digest. Empty history, unknown ID, incomplete candidate and altered staging checks passed. [Publication IDs and history evidence](evidence/M05-history.txt)

Publisher crash and concurrent reads (M06), later drills and hosted CI are **NOT RUN**. Next decision is M05 review.
