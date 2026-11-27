# ADR-0009 · Pin build inputs and review dependency updates

Status: Proposed
Date / proposed by: 27 November 2026 / Codex
Accepted by: Pending review
Reversibility: two-way door. Pins and update policy are versioned in Git.

## Context

A moving action tag or base-image tag can resolve to different bytes in a later build.

## Decision drivers

Keep today's runtime choices, make changes reviewable and retain the public-repository CI budget.

## Options considered and comparison matrix

| Choice | Repeatable dependency identity | Maintenance |
|---|---|---|
| Moving tags | No | Changes can arrive during a build |
| Immutable pins with manual discovery | Yes | Maintainer must find updates |
| Immutable pins with Dependabot proposals | Yes | Maintainer reviews update PRs |

## Decision

Use full upstream commit SHAs with release comments for GitHub Actions. Keep the Python image tag readable and append its verified multi-platform index digest. Configure weekly Dependabot checks for GitHub Actions and Docker at the repository root. Treat each proposed update as a code review.

## Why each alternative was rejected

Moving tags can change between reviews. Manual discovery makes it easier to miss an update.

## Consequences

Pins identify the selected inputs. They do not certify upstream code or freeze hosted runner images. The [security policy](../../SECURITY.md) describes how to request a private reporting channel. The first scheduled Dependabot update is **NOT VERIFIED**.

## Revisit when

A pinned action loses runner compatibility, the Python runtime changes or a relevant upstream security fix is published.

## Validation plan

Resolve the official release tags, compare the registry header with a hash of the index fetched by tag and digest, and build and run the offline verifier in CI. Review hosted session controls independently of dependency identity.

## Outcome

[MEASURED – Windows laptop, 27 November 2026] The upstream action refs resolved to the recorded releases. Both Docker registry reads returned the same index digest. [Verification excerpts](../evidence/task-4-supply-chain.txt)
