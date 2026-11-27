# Year-scale restart benchmark

## Protocol fixed before acquisition

Use all worldwide ComCat earthquakes with origin time in [2024-01-01, 2025-01-01) UTC. Apply no magnitude threshold. Fetch independent 12-day reference and 7-day ingestion windows, clipping only the final interval in each series. These two partitions span the same 366 days. Reuse the weekly demo's inclusive millisecond API encoding, exact body hashes, count validation and result ceiling. Fetch sequentially with bounded retries. Freeze the bodies, capture times, URLs and hashes before the offline drill.

In a fresh SQLite database, kill the real worker at the penultimate ingestion window after inserting its rows and checkpoint but before commit. Use a fresh connection to inspect rollback. Restart on the same file. Check skipped, replayed and previously unattempted windows separately. Compare every recovered ID, event time, source update time and magnitude with the independently parsed 12-day responses. Report duplicates before deduplication. A discrepancy fails the benchmark.

Measure worker restart to normal worker exit with a monotonic clock; report independent verification time separately. Report the closed SQLite file size. One laptop trial measures this workload and boundary only. The one-week interactive demo keeps its original fixture.

## Measured result

On 27 November 2026 IST, 84 independent HTTP requests (31 reference and 53 ingestion) returned 152,183 distinct earthquakes on each path, with zero retries. Reference bodies totaled 109,004,832 bytes and ingestion bodies 109,013,415 bytes. Each path covered the same leap year. Event count refers to unique IDs on one path. [Acquisition and worker transcript](../evidence/year-2024-restart.txt)

| Windows laptop, one offline trial | Observation |
|---|---|
| Kill boundary | December 23–29, after its 2,584 rows and checkpoint were written in an open SQLite transaction. The child signalled the parent, then Windows terminated it. |
| Fresh connection before restart | 51 committed checkpoints and 148,875 rows. The target had zero committed rows and no checkpoint. |
| Resume | Skipped writes for all 51 completed windows. Replayed 2,584 rows for December 23–29, then ingested 724 rows for December 30–31 for the first time. |
| Work repeated | Revalidated all 53 local ingestion bodies (109,013,415 bytes) before skip decisions. No network requests during recovery. |
| Elapsed | 8.237 s through first worker exit; 1.724 s from restart invocation through normal worker exit; another 12.278 s for independent row verification. |
| Final storage and equality | Closed ingestion database 55,554,048 bytes. Both sides had 152,183 raw and unique IDs; zero duplicates, missing IDs, extra IDs or records with field differences. |

The comparison uses a separate scratch SQLite database and projects the 12-day bodies independently. It compares numeric magnitude, UTC origin and update times, including null-aware magnitude equality. The final file size excludes the scratch database, source archive and working files. The timings describe a single run on already-read inputs. The annual drill measures ingestion and recovery; the one-week demo supplies the concurrent-reader and publication-history evidence.

## Reproduce from frozen responses

Download [comcat-2024.zip](https://github.com/puni344/earthquake-catalog-backfill/releases/download/comcat-2024-v1/comcat-2024.zip) to a writable local directory outside the checkout. From the checkout root, substitute that local ZIP and destination in these commands. Allow about 1 GiB of workspace for extracted data and temporary databases. Python with standard-library SQLite is sufficient.

```sh
python -m zipfile -e /path/to/comcat-2024.zip /path/to/comcat-2024
python -m earthquake.year verify /path/to/comcat-2024
```

Archive SHA-256: `1ab2db61a9b851cd63de14113468143368f4575cc7374fbcad33678509cb8a51`. The ZIP contains the 84 exact response bodies and a manifest with their original query URLs, timestamps, sizes, hashes and counts. The verifier creates and removes a fresh temporary database beside the extracted directory. Expect `YEAR PASS` and exit 0. To take a separate live capture, run `python -m earthquake.year capture /path/to/new-capture`; later captures can differ when USGS updates its catalog.
