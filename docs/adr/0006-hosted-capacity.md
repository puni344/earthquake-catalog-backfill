# ADR-0006 · Share hosted demo capacity across both workloads

Status: Proposed
Date / proposed by: 27 November 2026 / Codex
Accepted by: Pending review
Reversibility: two-way door. Admission and polling are confined to the hosted dashboard.

## Context

[SOURCE – hosted adapter] A paused annual run blocked even the first weekly visitor, whose page displayed Ready.

## Decision drivers

Keep sessions isolated, bound concurrent work and show visitors when they can start.

## Options considered and comparison matrix

| Option | Weekly and annual overlap | Maximum active |
|---|---|---|
| Exclusive workload type | Never | Two weekly or one annual |
| Independent limits | Yes | Three |
| Shared budget | Yes | Two, including at most one annual |

## Decision

Use a consistent lock order for both registries. Check the same admission rules on start and state polling. Active visitors can inspect and resume their own database even at capacity.

## Why each alternative was rejected

Exclusive workload types leave a weekly slot unused. Independent limits would increase the maximum number of workers.

## Consequences

A paused run occupies a slot until recovery or session expiry. Polling communicates availability without promising a reservation.

## Revisit when

Measured concurrent memory or latency calls for a different budget.

## Validation plan

Start a weekly run alongside a paused annual session, reject a third active visitor and admit work after recovery.

## Outcome

Public mixed-workload load measurement: **NOT RUN**. See the [hosted regression test](../../earthquake/test_hosted.py).
