# Earthquake catalog failure register

Proposed acceptance contract. Each drill uses frozen real responses. Faults are introduced only in a disposable copy. All drills below are NOT RUN. Evidence filenames are relative to docs/evidence/. The proposed runner is `python -m earthquake.verify --drill NAME` from the workspace root.

| NAME | Injection | Required behaviour | Proof / planned evidence |
|---|---|---|---|
| interrupted-fetch | Terminate during response write | Discard partial body and retry that window | Hash of resumed body equals frozen reference, quake-interrupted-fetch.txt |
| orphan-raw | Kill after raw rename, before checkpoint | Resume from validated local bytes | Zero extra requests for that verified body, quake-orphan-raw.txt |
| interrupted-commit | Kill between event insert and checkpoint | Roll back both, replay once | Per-window counts and zero duplicate keys, quake-interrupted-commit.txt |
| publish | Kill before and after pointer update with readers active | Readers see one complete generation per transaction | Every observed digest belongs to old or new, quake-publish.txt |
| boundary | Replay a real event on a split endpoint | Assign it to exactly one half-open interval | Reference ID set minus result and reverse difference both empty, quake-boundary.txt |
| missing | Withhold one real record from a cached child window | Block publication | Exact missing ID in anti-join, quake-missing.txt |
| duplicate | Repeat a real feature inside a response | Detect duplicate before uniqueness constraints hide it | Raw multiplicity and ID, quake-duplicate.txt |
| drift | Substitute a separately fetched source response | Freeze mismatching attempts for investigation | Reference and child hashes, timestamps and discrepant keys, quake-drift.txt |
| throttle | Return 429 then serve a real response | Honor Retry-After and resume same window | Attempt times, checkpoint and final hash, quake-throttle.txt |
| disk | Deny next staging write | Preserve readable published generation | Error code, prior manifest hash and reader result, quake-disk.txt |
