# ADR-0002 · Freeze independent whole-window and partitioned acquisitions

Status: Accepted

Date / proposed by: 25 November 2026 / Codex

Accepted by: puni344 on 25 November 2026

Reversibility: two-way door. Reacquire the source and rebuild manifests to change partitioning.

## Context

A mutable upstream makes a live retry ambiguous. The USGS query has inclusive boundaries and a response-size limit. The comparison needs a separately acquired reference. See the [design and measured constraints](../design/DESIGN-DOC.md).

## Decision drivers

Independent verification 50%, interruption recovery 30%, bounded transfer 20%.

## Options considered and comparison matrix

[ESTIMATE – paper evaluation on a 1–5 scale, higher is better] Columns follow the driver order above. Alternatives have not been benchmarked.

| Option | First driver | Second driver | Third driver |
|---|---|---|---|
| One live HTTP request | 2 · single source of truth | 1 · repeat entire request | 4 · low overhead |
| Offset-paged orchestrated sync | 2 · shifting page membership | 3 · page checkpoint | 3 · repeated page fetches |
| Fixed UTC windows and raw hashes | 5 · independent parent query | 5 · retry one window | 4 · parent adds traffic |

## Decision

Freeze exact response bytes, record acquisition metadata and reconcile IDs against the parent before publication. Window-level retries bound rework and cached bodies support offline drills.

## Why each alternative was rejected

A single response cannot independently establish partition coverage. Offset paging can skip or repeat IDs if an insertion changes ordering between requests. An orchestration service would still need a durable input manifest.

## Consequences

The independent parent costs an extra acquisition. A mismatch during live acquisition is inconclusive until the raw inputs are examined.

## Revisit when

A parent exceeds the documented service limit or a single timestamp cannot be split further. Reduce the audited period before claiming completeness.

## Validation plan

Run `python -m earthquake.verify --drill reconcile` and record two named verdicts in `docs/evidence/quake-reconcile.txt`.

1. **Live acquisition agreement.** Preserve the whole-window response bytes and independently acquired daily response bytes for the same fixed UTC interval, with timestamps and hashes. Count duplicate rows on each side before deduplication. List missing IDs and extra IDs separately. Retain the raw discrepancies and block publication until resolved.
2. **Frozen restart correctness.** Interrupt and resume the backfill offline on those same saved inputs. Independently compare recovered rows against the frozen reference. Report missing IDs, extra IDs, duplicate rows and field mismatches for matched IDs, including magnitude.

## Outcome

[MEASURED – M02, 26 November 2026] The whole-window and daily response bodies were independently acquired and frozen. Their sizes, hashes and recorded counts passed offline verification. [Acquisition evidence](../evidence/M02-acquire.txt)

[MEASURED – M03, 26 November 2026] Live acquisition agreement **PASS** for the frozen October fixture. Both acquisition paths had 2,569 unique IDs and zero excess rows. Missing IDs, extra IDs and projected field mismatches were all zero. Frozen restart correctness is **NOT RUN**, deferred to M04. [M03 transcript](../evidence/M03-reconcile.txt) The [intake evidence](../evidence/quake-machine.txt) and [source spike](../evidence/quake-detail.txt) establish prerequisites only.
