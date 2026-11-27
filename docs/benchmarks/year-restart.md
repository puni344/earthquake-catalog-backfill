# Year-scale restart benchmark

## Protocol fixed before acquisition

Use all worldwide ComCat earthquakes with origin time in [2024-01-01, 2025-01-01) UTC. Apply no magnitude threshold. Fetch independent 12-day reference and 7-day ingestion windows, clipping only the final interval in each series. These two partitions span the same 366 days. Reuse the weekly demo's inclusive millisecond API encoding, exact body hashes, count validation and result ceiling. Fetch sequentially with bounded retries. Freeze the bodies, capture times, URLs and hashes before the offline drill.

In a fresh SQLite database, kill the real worker at the penultimate ingestion window after inserting its rows and checkpoint but before commit. Use a fresh connection to inspect rollback. Restart on the same file. Check skipped, replayed and previously unattempted windows separately. Compare every recovered ID, event time, source update time and magnitude with the independently parsed 12-day responses. Report duplicates before deduplication. A discrepancy fails the benchmark.

Measure worker restart to normal worker exit with a monotonic clock; report independent verification time separately. Report the closed SQLite file size. One laptop trial measures this workload and boundary only. The one-week interactive demo keeps its original fixture.
