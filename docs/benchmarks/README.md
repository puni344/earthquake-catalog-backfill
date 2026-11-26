# Earthquake benchmarks

[MEASURED – Windows laptop, 26 November 2026] Four reader loops were the highest tested. All 168 timed responses passed the M06 ID-specific oracle. Every trial observed both publications and overlapped the normal publisher call. The reader counts below refer to complete CLI responses. M06 measures a separate forced crash.

| Loops | Timed reads | Successful reads/s | Median ms | P95 ms | Sampled peak MiB |
|---:|---:|---:|---:|---:|---:|
| 1 | 24 | 4.47 | 216.51 | 286.09 | 62.83 |
| 2 | 48 | 8.45 | 236.79 | 255.26 | 80.43 |
| 4 | 96 | 12.73 | 306.28 | 335.77 | 125.22 |

| Loops / repetition | Attempts / successes | Elapsed s | Successful reads/s | Median / p95 ms | Old / new | Reads overlapping publish | Errors / timeouts / mismatches | Sampled peak MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 / 1 | 8 / 8 | 1.774 | 4.51 | 223.03 / 280.77 | 1 / 7 | 1 | 0 / 0 / 0 | 54.46 |
| 1 / 2 | 8 / 8 | 1.755 | 4.56 | 214.77 / 251.88 | 2 / 6 | 2 | 0 / 0 / 0 | 58.78 |
| 1 / 3 | 8 / 8 | 1.840 | 4.35 | 216.79 / 288.12 | 2 / 6 | 2 | 0 / 0 / 0 | 62.83 |
| 2 / 1 | 16 / 16 | 1.919 | 8.34 | 238.41 / 261.98 | 4 / 12 | 4 | 0 / 0 / 0 | 79.13 |
| 2 / 2 | 16 / 16 | 1.870 | 8.56 | 232.60 / 255.26 | 4 / 12 | 4 | 0 / 0 / 0 | 80.23 |
| 2 / 3 | 16 / 16 | 1.892 | 8.46 | 237.71 / 249.05 | 4 / 12 | 4 | 0 / 0 / 0 | 80.43 |
| 4 / 1 | 32 / 32 | 2.589 | 12.36 | 318.64 / 343.53 | 8 / 24 | 8 | 0 / 0 / 0 | 125.22 |
| 4 / 2 | 32 / 32 | 2.455 | 13.03 | 302.10 / 323.21 | 8 / 24 | 5 | 0 / 0 / 0 | 118.20 |
| 4 / 3 | 32 / 32 | 2.494 | 12.83 | 303.05 / 330.13 | 8 / 24 | 4 | 0 / 0 / 0 | 119.04 |

Peak summed working set was 125.22 MiB, 546.78 MiB below the 672 MiB total design estimate and about 11,916 MiB below the M01 laptop ceiling. Samples included the harness, publisher and verifier in one process plus its live reader children. The sampling loop waited 20 ms between polls. Measured median sample spacing was 31.51 ms, with a maximum of 97.34 ms. Short peaks can be missed and shared pages can be counted twice. The estimate covers the full project; acquisition and an ingestion backlog were outside the timed workload. Higher concurrency, saturation, and sustained operation remain unmeasured.

[Predeclared protocol](m07-protocol.md) · [Raw samples and per-read results](../evidence/M07-load.txt) · [Separate publisher incident](../evidence/quake-publish.txt)
