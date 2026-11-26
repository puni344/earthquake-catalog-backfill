# Interrupted publication of the seven-day catalog

[MEASURED – Windows laptop, 26 November 2026] Four reader loops queried the current catalog while the drill extended coverage from 1–3 October to 1–7 October. The fault hook signaled after SQLite updated the current pointer inside the write transaction and paused before commit. After each reader completed a fresh read in that interval, the parent terminated publisher PID 22440 using Windows TerminateProcess. Its recorded exit status was -15. [Incident log](../evidence/quake-publish.txt)

| UTC | Observation |
|---|---|
| 12:31:58.164 | Baseline reading began. The shorter publication was current. |
| 12:31:59.113 | Parent received the open-transaction signal. All four readers subsequently completed an old-ID read before termination. |
| 12:31:59.592 | Parent initiated termination. |
| 12:31:59.603 | Exit confirmed. All four readers started and completed an old-ID observation before retry. |
| 12:32:00.211 | Normal publisher retry began against the same database. |
| 12:32:00.407 | Retry returned after commit. |
| 12:32:00.529 | First new-ID read finished verification. This read began before retry and spanned commit. Separately, all four loops started and completed fresh new-ID reads after commit confirmation. |

**Reader impact.** The 36 current reads all matched the expected ID-specific count and digest. The shorter extract remained usable through the deliberate outage. Final fresh processes retrieved 1,090 rows by the older ID and 2,569 by the newer ID. The two digests matched their respective whole-week-derived oracles.

**Recovery.** Kill initiation to first verified new read took 935.782 ms. Retry start to that observation took 317.162 ms. The 618.620 ms difference includes confirming exit and deliberately waiting for outage reads. These end-to-end timings include reader process execution, JSON parsing and digest verification.

**Measurement follow-up.** An initial run placed kill and confirmed exit on the same Windows monotonic clock tick. The reported run used the high-resolution monotonic performance counter and retained both transcripts. This incident exercised a single forced publisher exit with four readers on one laptop. Power loss, storage failure and load scaling remain untested. [Both runs and regression results](../evidence/M06-publish.txt) · [Operator procedure](../runbooks/publisher-recovery.md)
