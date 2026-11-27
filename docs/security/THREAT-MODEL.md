# Earthquake catalog threat model

| Asset and failure | Planned control | Remaining exposure |
|---|---|---|
| Frozen source bytes can be truncated or replaced | Record acquisition metadata and hashes before loading, then recheck on replay | Hashes alone cannot authenticate a source if both the manifest and body are replaced |
| A checkpoint can advance beyond written rows | Commit both in one local SQLite transaction | The planned drill covers process death; storage-device failure is outside its scope |
| A reader can observe mixed publication generations | Resolve the ID and read rows in one transaction, then compare with the independent digest for that ID | The reader drill samples a bounded workload |

Implementation checks are **NOT RUN**. [Publication decision](../adr/0003-catalog-storage.md)

## Hosted demo limits

[SOURCE – hosted adapter] Each weekly or annual session allows one active run and expires ten minutes after start. The two registries use separate cookies. The service allows two active runs overall, at most one annual run, and ten starts per minute per registry. There is no separate per-cookie or per-IP request-rate quota for reads or starts. [Session implementation](../../earthquake/hosted.py)

[MEASURED – Windows laptop, 27 November 2026, loopback Waitress 3.0.2] With the configured 1,024-byte body limit, a 1,023-byte POST reached the application. Waitress returned HTTP 413 at 1,024 and 1,025 bytes. The public Render proxy boundary is **NOT VERIFIED**. [Request and status excerpts](../evidence/task-4-supply-chain.txt)

The hosted regression exercises duplicate starts within a weekly cookie, shared capacity, simulated expiry and cross-session isolation. The production reaper's ten-minute wall-clock timing and the per-registry start-rate threshold are **NOT RUN** in that test. [Regression](../../earthquake/test_hosted.py)
