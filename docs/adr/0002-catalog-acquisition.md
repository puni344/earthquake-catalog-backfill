# ADR-0002 · Freeze independent whole-window and partitioned acquisitions

Status: Proposed  
Date / proposed by: 25 November 2026 / Codex  
Accepted by: pending user review  
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

Proposed command: `python -m earthquake.verify --drill reconcile`. Require both set differences empty and zero raw duplicates. Capture quake-reconcile.txt.

## Outcome

MVP validation NOT RUN. The [intake evidence](../evidence/quake-machine.txt) and [source spike](../evidence/quake-detail.txt) establish prerequisites only.
