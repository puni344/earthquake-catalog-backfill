# Check a failed catalog publication

Use this offline check after a publication attempt has finished and a fresh reader has queried current. The recorded expectation is the seven-day ID derived from the frozen whole-week reference.

## Triage a recorded attempt

From the repository root, run each command separately and inspect its exit code:

```sh
python -m earthquake.publication_alert check docs/evidence/task-5-publication-alert/incomplete.json
python -m earthquake.publication_alert check docs/evidence/task-5-publication-alert/recovered.json
```

| Exit | Meaning | Operator action |
|---|---|---|
| 1, ALERT | Publisher rejected the candidate or the verified current ID differs from the expected ID. | Inspect the record's reason, expected ID and current read. Keep the previous release available. |
| 2, INCONCLUSIVE | Signal is missing, unreadable, malformed, or lacks a successful current read after the attempt. | Obtain a fresh observation and inspect the recorder before treating the incident as resolved. |
| 0, OK | The recorded attempt succeeded and its verified post-attempt read returned the expected ID. | Retain the failed and successful records together. |

For a missing checkpoint, finish ingesting the declared scope from the frozen inputs on the same database. Retry through the normal publisher, then query current again. Preserve both records. The [publisher recovery procedure](publisher-recovery.md) includes commands for inspecting both publication IDs. Never manually advance the pointer or insert a completion checkpoint.

## Reproduce the injection

Choose a new output directory. The drill refuses to overwrite it. Its SQLite database is disposable, and the signal files survive cleanup.

```sh
python -m earthquake.publication_alert drill alert-run
```

This stages three days, publishes that complete scope, then attempts to publish the week early. After recording the rejection and running the check, the drill finishes ingestion and retries. No network connection or separate alert service is needed. [Actual transcript](../evidence/task-5-publication-alert.txt)

The checker evaluates one completed attempt. It cannot detect a publisher that never returns or a recorder that never emits a file unless someone invokes the check on the missing file. Its result describes the recorded read; replay does not poll a live database.
