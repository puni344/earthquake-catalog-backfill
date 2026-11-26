# Measured results and limits

Measurements below were taken on a Windows 11 laptop with an i5-1235U and 12 logical processors on 26 November 2026. Each row identifies the experiment that produced it. [Hardware](evidence/quake-machine.txt)

| Run | Workload and measured result |
|---|---|
| [M02/M03 acquisition](evidence/M03-reconcile.txt) | One whole week and seven daily HTTP responses for October 1–7. Both paths yielded 2,569 unique events with zero missing, extra, duplicate or changed projected values. |
| [M08 integrated worker crash](evidence/quake-verify.txt) | 3.349 s. The October 4 pre-commit kill left zero target rows. Resume skipped three days and recovered 2,569 rows. All 23 current reads verified. Final IDs returned 1,090 and 2,569 rows. |
| [M06 publisher crash](evidence/quake-publish.txt) | Four reader loops, 36 verified current reads. Forced exit after the pointer update and before commit. First verified new read took 935.782 ms from kill and 317.162 ms from retry. |
| [M07 normal publication under load](benchmarks/README.md) | Three trials each at 1, 2 and 4 reader loops, eight timed CLI reads per loop. All 168 passed. Four loops delivered 12.73 reads/s, pooled p95 335.77 ms, peak sampled summed working set 125.22 MiB. |
| [M07 acquisition repair](evidence/M07-orphan-remediation.txt) | After a worker kill, restarting the intact whole response went from one redundant request (1,839,817 bytes) to zero. All ten register entries passed after remediation. |
| [M09 clean clone](evidence/M09-clean-clone.txt) | Candidate `a39b613`, fresh Windows PowerShell. Make exited 0 in 3.754 s wall time, including 3.283 s inside the verifier. All 24 current reads and both final lookups verified. |

The reference establishes agreement between two query paths for one captured week. The two publications cover different dates. Revision history of individual earthquakes, power-loss durability, multi-host failover, saturation and sustained throughput remain unverified. [Hosted Linux crash test](https://github.com/puni344/earthquake-catalog-backfill/actions/workflows/hosted.yml) · [Documentation CI](https://github.com/puni344/earthquake-catalog-backfill/actions/workflows/earthquake-docs.yml). [Accepted ADRs](adr/README.md) · [Failure register](failure-register.md) · [Interview materials and score](DEFENCE.md) · [Project state](PROJECT_STATE.md)

## Cross-platform full verifier

Commit `265e739` exercised the same frozen week, worker termination, rollback inspection, restart, concurrent current reads and both final historical-ID lookups on all three targets. Both acquisition agreement and frozen restart correctness passed in every job. The timings below are single-run verifier measurements. [Complete CI transcripts](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45877167536)

| Execution | Python / SQLite | Verifier elapsed | Verified current reads | Errors / timeouts / mismatches |
|---|---|---:|---:|---|
| Native Ubuntu x86-64, `make verify` | 3.15.2 / 3.46.1 | 2.690 s | 33 | 0 / 0 / 0 |
| Native macOS arm64, `make verify` | 3.15.2 / 3.53.4 | 2.719 s | 25 | 0 / 0 / 0 |
| Docker Linux x86-64, non-root, network disabled | 3.11.14 / 3.40.1 | 3.255 s | 19 | 0 / 0 / 0 |

The first native CI attempt stopped at interpreter installation. Selecting the runner's available Python 3 release resolved that portability issue. [Initial CI attempt](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45877071374)
