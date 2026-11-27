# Weekly publication rejected with four days still pending

[MEASURED – 27 November 2026, Windows laptop, Python 3.10.11, SQLite 3.40.1] In a fresh drill database the October 1–3 release was current. The injection requested October 1–7 before staging October 4–7. The publisher rejected the first missing checkpoint, October 4. A fresh CLI read verified the old release and its 1,090 rows. The offline check emitted ALERT and exited 1. [Transcript](../evidence/task-5-publication-alert.txt) · [Failure signal](../evidence/task-5-publication-alert/incomplete.json)

**Impact and recovery.** The previous release remained readable. The simulated consumer expecting the week still saw the shorter extract. Resuming normal ingestion on the same database supplied the outstanding checkpoints. The retry published the expected week, the reader verified 2,569 rows, and the check returned OK with exit 0. [Recovery signal](../evidence/task-5-publication-alert/recovered.json)

**Lesson.** A successful read of current only establishes availability. It took an independently expected publication ID and an observation after the attempt to establish whether the requested week was available. Preserve both signals when following the [alert runbook](../runbooks/publication-alert.md).
