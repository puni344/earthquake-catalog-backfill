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

[MEASURED – M06, Windows laptop, 26 November 2026] Publisher crash drill **PASS**. Four CLI reader loops made 36 current reads across one forced pre-commit publisher exit and retry. All returned complete known publications. The first verified new read finished 935.782 ms after kill initiation and 317.162 ms after retry began. Both historical IDs remained readable. [Per-read evidence](evidence/quake-publish.txt) · [Postmortem](postmortems/m06-publisher-crash.md)

[MEASURED – M07, Windows laptop, 26 November 2026] Nine fresh-state trials at 1, 2 and 4 reader loops passed. All 168 timed reads matched the independent publication oracle. Four loops were the highest tested. Register review: **9 PASS, 1 FAIL, 0 NOT RUN**. Acquisition restart refetched the already verified orphan body once, reproducing its hash. That run left the zero-extra-request requirement open. [Load summary](benchmarks/README.md) · [Register verdicts](failure-register.md)

On 26 November 2026 the orphan rerun passed. Resuming the named acquisition reused the verified whole response and fetched seven outstanding daily responses. Final M07 register totals are **10 PASS, 0 FAIL, 0 NOT RUN**. The original benchmark supplies the publication measurements. [Remediation evidence](evidence/M07-orphan-remediation.txt)

M08 passed on 26 November 2026. The default offline command completed in 3.349 s on one disposable database. Three checkpoints survived the worker kill, October 4 replayed and all 2,569 recovered rows agreed with the reference. All 23 current reads and both final historical lookups verified. [Integrated transcript](evidence/quake-verify.txt) and [regression evidence](evidence/M08-verify.txt).

**M09 passed and D2 is complete.** On 26 November 2026 a new Windows shell resolved GNU Make 4.4.1 from the per-user WinGet package directory. A local clone of `a39b61362f7db556b841b8395d885af8b99f4b11` passed `make verify` offline in 3.754 s wall time. Both acquisition and restart verdicts passed. All 24 current reads and the final 1,090-row and 2,569-row ID lookups verified. Final score **79/100**. Hosted CI is **NOT RUN**. The original milestone review used an unpublished local checkout. [Clean-clone evidence](evidence/M09-clean-clone.txt) · [Recording script, three résumé bullets, twenty interview answers and rubric](DEFENCE.md)

The local presentation dashboard pauses after the verified worker termination. Browser checks covered querying the shorter edition during interruption, continuing recovery, reading the week, reopening and paging the older rows, rejecting a duplicate start and rerunning. [Browser observations](evidence/dashboard-browser.txt) · [Presentation decision](adr/0004-dashboard.md)
