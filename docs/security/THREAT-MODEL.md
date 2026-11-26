# Earthquake catalog threat model

| Asset and failure | Planned control | Remaining exposure |
|---|---|---|
| Frozen source bytes can be truncated or replaced | Record acquisition metadata and hashes before loading, then recheck on replay | Hashes alone cannot authenticate a source if both the manifest and body are replaced |
| A checkpoint can advance beyond written rows | Commit both in one local SQLite transaction | The planned drill covers process death; storage-device failure is outside its scope |
| A reader can observe mixed publication generations | Resolve the ID and read rows in one transaction, then compare with the independent digest for that ID | The reader drill samples a bounded workload |

Implementation checks are **NOT RUN**. [Publication decision](../adr/0003-catalog-storage.md)
