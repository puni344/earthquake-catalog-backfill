# ADR-0008 · Verify the pinned runtime on a hosted Windows runner

Status: Proposed
Date / proposed by: 27 November 2026 / Codex
Accepted by: Pending review
Reversibility: two-way door. The existing Windows preflight remains the runtime authority.

## Context

The laptop drills use ADR-0003's Python and SQLite pins. The native CI matrix previously covered Ubuntu and macOS.

## Decision drivers

Exercise the Windows process boundary in a fresh checkout, preserve runtime compatibility and keep hosted execution on standard public-repository runners.

## Options considered and comparison matrix

| Route | Validates the pinned Windows runtime | Requires laptop access |
|---|---|---|
| Laptop only | Yes | Yes |
| Windows hosted runner with both pins checked | When the pins match | No |
| Hosted runner with relaxed pins | No | No |

## Decision

Select x64 Python 3.10.11 on windows-latest. Log the OS, executable and SQLite library from that interpreter. If Python and SQLite match ADR-0003, run make verify and make test. If the interpreter is installed but its versions differ, log the mismatch and run the acquisition, reconciliation, controlled preflight and evidence tests. Interpreter installation and other unexpected failures remain visible CI failures.

## Why each alternative was rejected

Laptop-only checks depend on a particular checkout. Accepting another SQLite build would change the contract for the audited Windows drill.

## Consequences

The hosted job validates the workload on the runner it prints. Laptop timings and resource measurements retain their original scope.

## Revisit when

The runner no longer supplies the pinned interpreter or ADR-0003 changes.

## Validation plan

Inspect the hosted job's runtime line, actual Make steps and terminal verdicts. Save the observed output or the specific blocker.

## Outcome

See the [Windows CI workflow](../../.github/workflows/verify.yml).
