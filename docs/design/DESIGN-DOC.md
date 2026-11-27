# Turn 3 · Restartable USGS earthquake catalog

**Decision for review.** The requested first choice was integrated D1. The attached cutoff was 23 November 2026, 20:00 IST, including failure to start capture. No qualifying pre-cutoff pair was available in this workspace or supplied materials. Apply D2. The P1 publication drill and S1 named-history query remain part of the design. A later observation may support a future D1 proposal.

## Users and acceptance

An analyst needs a complete catalog for a fixed period. An operator needs to restart a failed download and establish which extract readers could query during recovery. Given a frozen parent response and independently downloaded child windows, does a killed and resumed run reproduce the reference ID set, with zero duplicate IDs, while readers continue seeing complete published extracts? A reviewer should be able to replay this offline, query the old and new manifests, and inspect a discrepant ID in five minutes (design target).

## Evidence available now

[MEASURED – Windows intake and USGS requests, 25 Nov 2026] [Machine log](../evidence/quake-machine.txt), [runtime](../evidence/quake-runtime.txt), [collector log](../evidence/quake-capture.txt), [origin versions](../evidence/quake-detail.txt). A 159,943-byte rolling response contained 225 features. For us6000udd1 the current detail contained one US origin and the superseded catalog response contained two US origin versions with the same code and magnitude 5.9. Each response has one top-level preferred magnitude. Historical public display remains unverified. Retrieval time and feed generation time are distinct. The daily feed is spike evidence only.

[SOURCE: USGS documentation, checked 25 Nov 2026] The [catalog query](https://earthquake.usgs.gov/fdsnws/event/1/) supports event-specific superseded products and up to 20,000 events per query. Bounds include both endpoints. The [summary feed](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) refreshes every minute. Numeric service request quota unverified. Credit U.S. Geological Survey and retain contributor attribution. USGS-produced data are in the US public domain. Review third-party material separately before redistribution. [USGS terms](https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted)

## Data flow and publication

**M02 extract specification, recorded before fetching on 26 November 2026.** Use worldwide earthquakes with no magnitude or review-status filter, from 2026-10-01 00:00 UTC inclusive to 2026-10-08 00:00 UTC exclusive. Issue one whole-week GeoJSON request and seven independent daily requests, each ordered by ascending origin time. Midnight belongs to the day starting at that instant. USGS includes both query endpoints and reports origin times as integer epoch milliseconds. Send the inclusive end as 23:59:59.999Z of the final included day, the immediate predecessor on that timestamp grid. Omit pagination and an explicit limit. Reject a response reaching the service ceiling of 20,000 features or showing a truncation warning. [USGS query contract](https://earthquake.usgs.gov/fdsnws/event/1/) · [ComCat origin-time precision](https://earthquake.usgs.gov/data/comcat/data-eventterms.php#time)

1. Request a closed historical UTC week (proposed 1–8 October 2026, end exclusive). Download a whole-window reference and daily partitions independently, filtering to earthquake events with the same predicates. Save request URL, fetch time, status, byte length, SHA-256 and exact body before parsing. For millisecond timestamps send inclusive end equal to exclusive end minus 1 ms. Split oversized windows by time and fail explicitly if the smallest representable window still exceeds the service limit. Keep the reference small enough to acquire independently.
2. Detect duplicate IDs before inserting. Verify count, schema and window membership, including valid empty windows. Compare child IDs in both directions with a separate reference reader. Compare projected event values separately. A live reference mismatch blocks release and records both acquisitions. Freeze mutually consistent inputs for the deterministic crash drill.
3. Store immutable response blobs by hash. In one local SQLite transaction, insert staged observations and mark the corresponding window complete. Restart verifies cached hashes before reuse. Use a local working directory outside OneDrive synchronization for the active SQLite database. Export closed evidence files into the repository.
4. Model acquisition(window, attempt, body_hash, fetched_at), observation(body_hash, event_id, event_time, source_updated, magnitude_nullable), generation(id, manifest_hash), member(generation, event_id, body_hash), active(singleton, generation). Keep immutable generations. Publish only a fully reconciled generation by changing active in one commit. Each reader opens one read transaction before resolving active.
5. Proposed CLI: `history OLD NEW` lists added, removed and changed IDs, source timestamps and raw hashes. Show two named, documented extract windows if the catalog has no genuine corrections. Label a change in extract coverage explicitly. A difference between windows says nothing about magnitude revision.

## Scope, constraints and resource budget

### M03 comparison contract (specified before the drill)

Key each observation by the exact, case-sensitive GeoJSON feature ID. Compare the observation fields `event_time` (properties.time) and `source_updated` (properties.updated) as integer epoch milliseconds, and `magnitude` (properties.mag) by exact decimal numeric value with no rounding or tolerance. Explicit null magnitude equals only null. Every projected key must exist; a missing key or null timestamp fails input validation. M02 also validates the earthquake type and time-window membership.

Count every feature before grouping. Across all files on each side, report raw rows, distinct IDs, IDs occurring more than once and rows beyond the first per ID. Every duplicate fails. Compare reference-only and daily-only IDs separately. For each shared ID, compare the set of observed values for each projected field, reporting one mismatch per ID and field with all contributing file locations. Duplicate multiplicity has its own check. Row order, request metadata and body hashes are outside field equality; the hashes identify the independently validated source files. A failed verdict blocks eligibility for publication.

[MEASURED – machine log, 25 Nov] 15.68 GiB visible physical RAM, 3.37 GiB free at intake, 10 cores / 12 logical CPUs and 224.42 GiB free on C:. Windows 11, UEFI, Docker Linux engine verified. WSL2 Docker distribution listed. Hypervisor present. The firmware virtualization property returned false. [Machine and container output](../evidence/quake-machine.txt)

[NOT VERIFIED] Native dual boot, application deadline and monthly data cap.

[ESTIMATE – one writer, small historical week, offline replay] Proposed ceilings, to measure under load:

| Component | RAM MiB | CPU cores | Disk MiB |
|---|---:|---:|---:|
| Downloader and raw staging | 128 | 1 | 256 |
| SQLite writer and indexed generations | 256 | 1 | 384 |
| Reference checker and concurrent readers combined | 256 | 2 | 128 |
| Logs and evidence | 32 | 0.1 | 128 |
| Total | 672 | 4.1 | 896 |

The estimated total is below 75% of measured RAM and below observed free RAM. Keep the MVP on native Python with local disk. Stop acquisition at the configured byte cap. [ESTIMATE – five hours/day, includes rehearsal] Acquisition and reconciliation 10–14 hours, publication and crash drill 6–9, history and review 4–7. Total 20–30 hours over 4–6 working days. Stretch only after acceptance: larger windows, a web API or a containerized replay. Cloud allocation ₹0. Use existing hardware and connection, no cloud signup, deployment, credits or teardown dependency; mobile data allowance unverified.

### M01 capacity and state directory

[MEASURED – Windows laptop, 26 November 2026] `python -m earthquake.verify --drill preflight` measured 16,055.36 MiB visible RAM, 3,520.49 MiB available RAM, 12 logical processors and 231,854.48 MiB free on the fixed C: volume at the state directory. The 672 MiB design estimate fits both available RAM and the 12,041.52 MiB ceiling (75% of visible RAM). The 896 MiB disk estimate fits that volume. CPU is reported as logical processors alongside the design estimate in cores. Application memory use and CPU performance await load measurement. [Preflight transcript](../evidence/M01-preflight.txt)

The Windows default for mutable state is `%LOCALAPPDATA%/D2EarthquakeCatalog/state`. The preflight resolves the path and checks it against the resolved checkout, OneDrive environment roots and current-user OneDrive account registry folders. It identifies the containing volume as fixed and verifies SQLite create, commit, close, read-only reopen and read inside a unique disposable directory. This establishes path exclusion for the roots visible to this account at check time. Other sync software, undiscovered sync roots and future configuration changes are outside the check.

### M05 publication identity and reader encoding

A publication covers whole UTC days with an inclusive start and exclusive end. The two M05 scopes end at midnight on 4 and 8 October. Before advancing the pointer, the writer verifies the frozen response bodies, requires every scoped daily checkpoint, checks the staged rows against each daily body and reconciles them against the independently filtered whole-week reference. A single SQLite transaction copies the verified member values into publication-specific rows and advances the singleton current pointer. Repeating an identical publish reuses the ID. Reads resolve the pointer or explicit ID and fetch members within one read transaction.

For the row digest, order the array by case-sensitive event ID (SQLite BINARY). Each object contains event_id, event_time, source_updated and magnitude. Times are integer epoch milliseconds. Magnitudes are null or plain decimal strings with insignificant fractional zeros removed and zero encoded as "0". Encode the array as UTF-8 JSON with sorted object keys, compact separators, literal non-ASCII characters and no trailing newline. Hash those bytes with SHA-256.

The publication ID is the full lowercase SHA-256 of the metadata object under the same encoding. Its keys are schema (1), fixture, manifest_sha256, start, end_exclusive, reference_sha256, daily_sources (UTC date to body SHA-256), count and rows_sha256. The ID itself is added only to returned metadata. The expanded window changes coverage; these two extracts make no claim of a source magnitude revision. [Reader evidence](../evidence/M05-history.txt)

## Benchmarks and evidence contract

All planned commands below are proposed interfaces, UNVERIFIED / NOT RUN. For baseline and resumed runs use identical frozen bytes and record manifest hash, OS, runtime, free RAM, window count and event count. Use monotonic clocks and record each run separately.

| Proposed command | Measurement and acceptance target | Planned output in docs/evidence/ |
|---|---|---|
| python -m earthquake.verify --drill replay | Three cold replays. Log elapsed time, peak working set, actual disk and bytes fetched. Offline network requests = 0. | quake-replay.txt |
| python -m earthquake.verify --drill reconcile | Emit missing IDs, extra IDs and raw duplicates separately. All empty on baseline. | quake-reconcile.txt |
| python -m earthquake.verify --drill publish | Four readers during each kill boundary. Log read generation/digest, latency p50/p95, sample count, worst recovery time. Require reads spanning the boundary and zero mixed results. | quake-publish.txt |
| python -m earthquake.verify --drill history | Recompute every delta from raw files in an independent reader. Require identical IDs and coverage labels. | quake-history.txt |
| python -m earthquake.verify | One-command offline demo, aggregate drill exit codes, fail on any broken invariant. | quake-verify.txt |

[Failure register](../failure-register.md) specifies fault injection and expected evidence. No measured recovery time, peak usage or completeness result exists yet.

## Design challenges and revisions

| First review objection | Revision | Second review objection | Revision |
|---|---|---|---|
| Another catalog downloader | Require exact discrepancies and interrupted replay | Matching totals can hide swapped IDs | Anti-join in both directions |
| Concurrent source edits invalidate verification | Freeze independent acquisitions | Freezing the same response twice proves little | Acquire parent and partitions independently |
| Restart log proves little | Keep readers querying through process kill | Idle readers can miss a broken transition | Require time-stamped reads across each kill boundary |
| History could imply a fake revision | Record UTC window and generation | Moving the window explains membership only | Report coverage changes separately from same-ID changes |
| Local demo depends on live internet | Include frozen input and offline command | A second parser can repeat the first bug | Independently enumerate reference features and inject real omissions and duplicates |

## Review score

[ESTIMATE – proposal review, no MVP implementation credit] Scores reflect inspectable work today; projections assume all corresponding evidence passes.

| Dimension | Today | After acceptance (estimate) | Anchor |
|---|---:|---:|---|
| Role relevance | 13/20 | 17/20 | SQL completeness, reader recovery and history contracts above |
| Technical depth | 7/20 | 15/20 | [Persistence decision](../adr/0003-catalog-storage.md) |
| Production readiness | 2/20 | 14/20 | [Fault and load contracts](../failure-register.md); drills pending |
| Differentiation | 4/15 | 10/15 | Independent reference plus resumed result; signature result pending |
| Demonstrability | 4/15 | 12/15 | [Real endpoint evidence](../evidence/quake-detail.txt); offline demo pending |
| Cost and reproducibility | 4/10 | 9/10 | [Local runtime](../evidence/quake-runtime.txt); clean one-command replay pending |
| Total | 34/100 | 77/100 | Re-score from saved outputs after implementation |
