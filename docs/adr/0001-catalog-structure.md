# ADR-0001 · Keep one catalog project with three review paths

Status: Accepted

Date / proposed by: 25 November 2026 / Codex

Accepted by: puni344 on 25 November 2026

Reversibility: two-way door. Dropping a review path costs its demo and tests.

## Context

The D1 gate expired. D2 has a verifiable completeness question even when no event changes. The same extract can exercise the publishing and history interfaces. See the [design and measured constraints](../design/DESIGN-DOC.md).

## Decision drivers

Review time 40%, evidence quality 40%, role coverage 20%.

## Options considered and comparison matrix

[ESTIMATE – paper evaluation on a 1–5 scale, higher is better] Columns follow the driver order above. Alternatives have not been benchmarked.

| Option | First driver | Second driver | Third driver |
|---|---|---|---|
| One backfill only | 5 · shortest review | 3 · no reader drill | 2 · primarily data |
| Two independent repositories | 2 · repeat setup | 3 · separate proof inputs | 5 · dedicated demos |
| Integrated backfill | 4 · shared setup | 5 · identical frozen inputs | 5 · three interfaces |

## Decision

Use one reference extract, one crash scenario and one generation history. This gives all three roles a concrete question about the same data.

## Why each alternative was rejected

A data-only build drops the reader-visible incident. Two repositories require separate installs and a second realistic incident workload. [ESTIMATE – earlier intake] Two projects require 42–62 review/build hours versus 20–30 for the scoped fallback.

## Consequences

One walkthrough can reuse captured inputs. Failure in reference acquisition can delay every demo. Keep a small independently verified frozen period.

## Revisit when

Review effort exceeds 30 hours or the application deadline cannot accommodate the integrated demo.

## Validation plan

In one offline invocation of `python -m earthquake.verify`, interrupt a backfill, resume it, compare the recovered extract with the independent frozen reference, and retrieve both previous and new publications by ID. Save the command and result in `docs/evidence/quake-verify.txt`.

## Outcome

[MEASURED – M05, 26 November 2026] Both scoped extracts were retrieved by ID after the current pointer advanced. [History drill](../evidence/M05-history.txt). The [intake evidence](../evidence/quake-machine.txt) and [source spike](../evidence/quake-detail.txt) establish prerequisites only.

M08 passed on 26 November 2026. One offline invocation interrupted and resumed the backfill and verified both publication IDs on one database. [Integrated verification](../evidence/quake-verify.txt)
