# Earthquake catalog failure register

Proposed acceptance contract. Each drill uses frozen real responses. Faults are introduced only in a disposable copy. The ingestion commit and M06 post-pointer-update drills have run. The M06 evidence covers the interval before the publisher commits. [M02 acquisition faults](evidence/M02-acquire.txt) exercised the acceptance gate: an injected disconnect after 512 real bytes on each bounded attempt retained partial staging files without a completed manifest. A same-length byte change in a disposable fixture blocked completion on SHA-256 verification. Network-fetch resumption is still untested. Evidence filenames are relative to docs/evidence/. The proposed runner is `python -m earthquake.verify --drill NAME` from the workspace root.

[MEASURED – M03, offline, 26 November 2026] Disposable copies of verified observations exercised the missing and duplicate detection gates, an extra ID and a magnitude change under the same ID. The equal-count replacement yielded 2,569 daily rows, 2,568 unique IDs, one missing ID and one excess duplicate row. Failed reconciliation marks the extract ineligible. M05 then removed the 5 October checkpoint in a disposable database and, separately, changed staged magnitudes. Both candidates failed and the existing publication remained current. [M05 gate evidence](evidence/M05-history.txt). [Fault diagnostics](evidence/M03-reconcile.txt)

| NAME | Injection | Required behaviour | Proof / planned evidence |
|---|---|---|---|
| interrupted-fetch | Terminate during response write | Discard partial body and retry that window | Hash of resumed body equals frozen reference, quake-interrupted-fetch.txt |
| orphan-raw | Kill after raw rename, before checkpoint | Resume from validated local bytes | Zero extra requests for that verified body, quake-orphan-raw.txt |
| interrupted-commit | Kill between event insert and checkpoint | Roll back both, replay once | [M04 process termination and checkpoint evidence](evidence/M04-restart.txt) |
| publish | Kill before and after pointer update with readers active | Readers see one complete generation per transaction | [M06 after pointer update, before commit](evidence/quake-publish.txt). A separate pre-update kill remains NOT RUN. |
| boundary | Replay a real event on a split endpoint | Assign it to exactly one half-open interval | Reference ID set minus result and reverse difference both empty, quake-boundary.txt |
| missing | Withhold one real record from a cached child window | Block publication | Exact missing ID in anti-join, quake-missing.txt |
| duplicate | Repeat a real feature inside a response | Detect duplicate before uniqueness constraints hide it | Raw multiplicity and ID, quake-duplicate.txt |
| drift | Substitute a separately fetched source response | Freeze mismatching attempts for investigation | Reference and child hashes, timestamps and discrepant keys, quake-drift.txt |
| throttle | Return 429 then serve a real response | Honor Retry-After and resume same window | Attempt times, checkpoint and final hash, quake-throttle.txt |
| disk | Deny next staging write | Preserve readable published generation | Error code, prior manifest hash and reader result, quake-disk.txt |
