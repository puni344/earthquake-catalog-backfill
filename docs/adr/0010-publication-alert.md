# ADR-0010 · Detect a failed publication from a recorded attempt

Status: Proposed
Date / proposed by: 27 November 2026 / Codex
Accepted by: Pending review
Reversibility: two-way door. The offline checker reads signal files independently of the publisher.

## Context

A previous complete release can remain available when the requested release fails. A healthy reader alone can miss this failure.

## Decision drivers

Preserve the usable old release, distinguish a failure from insufficient evidence, and let reviewers replay the decision without recreating the database.

## Options considered and comparison matrix

| Signal | Establishes |
|---|---|
| Reader exit status alone | A release could be read |
| Wall-clock age of current | Time since publication, given an agreed freshness deadline |
| Attempt outcome plus a post-attempt current read | Whether the requested publication was available after that attempt |

## Decision

Record the publisher outcome, the independently expected ID, and a fresh current CLI observation checked against the scoped reference. The recorder uses a single monotonic clock to order attempt completion and the read. A separate command consumes the saved record. It exits 1 for a rejected attempt or an unexpected current ID, 0 for a successful attempt with the expected ID, and 2 for unusable evidence.

## Why each alternative was rejected

An HTTP or CLI success misses stale releases. The offline fixture has no delivery schedule from which to derive a freshness deadline.

## Consequences

Replay trusts the local recorder's reference check and timestamps. It neither authenticates the record nor rechecks rows from a deleted database. The operator supplies a completed attempt to the checker. There is no scheduler, notification channel or calendar-based freshness guarantee.

## Revisit when

The catalog has a delivery schedule, a persistent event source or a consumer requiring unattended notification.

## Validation plan

Attempt to publish a complete week while only its first three days are staged. Check the recorded failure, finish ingestion and retry on the same database. Replay both records through the checker.

## Outcome

[MEASURED – Windows laptop, 27 November 2026] The checker alerted on rejection and cleared after retry. The offline drill exited 0 after observing both expected checker exits. [Command and raw output](../evidence/task-5-publication-alert.txt)
