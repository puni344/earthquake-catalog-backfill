# ADR-0004 · Local presentation dashboard

Status: Proposed
Date / proposed by: 26 November 2026 / Codex
Accepted by: Pending review
Reversibility: two-way door. The CLI is independent of the browser view.

## Context

A presenter needs time to inspect a readable publication between a worker kill and restart.

## Decision drivers

Show actual state, keep the demo offline and retain both editions for inspection.

## Options considered and comparison matrix

| Option | Inspect during outage | Runtime |
|---|---|---|
| CLI transcript | Historical observations | Existing Python |
| Local HTTP screen | Live SQLite reads and manual resume | Existing Python and browser |
| Frontend framework | Same database operations | Additional toolchain |

## Decision

Serve bundled HTML, CSS and JavaScript on IPv4 loopback. A single background run owns a temporary database. After the October 4 worker exits, open a fresh SQLite connection, inspect rollback, verify the current edition and wait for explicit continuation.

## Why each alternative was rejected

The CLI finishes before a presenter can browse the stopped state. A separate frontend build adds no capability needed by this screen.

## Consequences

A second start during a run returns HTTP 409. Refreshing the browser reconnects to the active state. Recovery timing is omitted because the operator controls the pause.

## Revisit when

Multiple independent sessions or remote access would require a different server and access model.

## Validation plan

Use a browser to read the old edition during interruption, continue, verify the week, reopen the original edition and run again.

## Outcome

The Edge walkthrough passed, including pagination and duplicate-start rejection. [Browser evidence](../evidence/dashboard-browser.txt)
