# Earthquake project state

Turn 3 design ready for review. The 23 November 2026 20:00 IST D1 gate expired without a qualifying captured pair. D2 is active. Retain P1 and S1 against named catalog generations. [Design and evidence](design/DESIGN-DOC.md).

[MEASURED – 25 November 2026] Windows and Docker checks, one timestamped daily snapshot, ordinary detail and superseded-product response saved. Capture command from workspace root: `python earthquake/scripts/capture_usgs.py`. Optional bounded sampling: `python earthquake/scripts/capture_usgs.py --minutes 30` (one process, five-minute interval, 128 MiB cap). No ongoing collector required after fallback. [Raw capture log](evidence/quake-capture.txt).

Review [structure](adr/0001-catalog-structure.md), [acquisition](adr/0002-catalog-acquisition.md), and [publication/runtime](adr/0003-catalog-storage.md). Next is Turn 4 after ACCEPT or CHANGE. Planned drill commands are NOT RUN.
