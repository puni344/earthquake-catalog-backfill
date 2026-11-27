# ADR-0005 · Portable scratch state outside Windows

Status: Proposed
Date / proposed by: 27 November 2026 / Claude (review pass)
Accepted by: Pending review
Reversibility: two-way door. Only `restart.state_directory()` changes; the Windows path keeps its audited checks.

## Context

`make verify` already ran on Linux and macOS, but the history, publish and restart drills and eight unit tests still called the Windows-only preflight (`winreg`, `kernel32`, Python 3.10.11 and SQLite 3.40.1 pins). On Linux they failed with "local state preflight failed", so the history commands in the reproduction guide could not be followed there and CI exercised only the default command.

## Decision drivers

Keep every Windows measurement and check exactly as audited. Let a reviewer on Linux or macOS run every drill. Do not weaken the isolation of drill databases from the checkout.

## Options considered and comparison matrix

| Option | Windows evidence unchanged | Drills run on Linux and macOS | Isolation |
|---|---|---|---|
| Keep Windows-only drills and document that | Yes | No | Existing |
| Relax the preflight everywhere | No: changes audited checks | Yes | Weaker |
| Branch only the state directory by platform | Yes | Yes | Private per-user directory |

## Decision

On Windows, `state_directory()` still runs the preflight and returns the checked LOCALAPPDATA location. Elsewhere it returns a private directory: `EQ_STATE_DIR` if set, otherwise `<tmp>/d2-earthquake-catalog-<uid>`, created mode 0700. It refuses a directory owned by another user or writable by group or others. The preflight's OS test moved into `native_windows()` so its controlled-failure tests run on any platform. The load benchmark samples Windows working sets, so elsewhere it prints a skip message and exits 2.

## Why each alternative was rejected

Documenting Windows-only drills leaves the Linux reader with commands that fail, and leaves most unit tests outside CI. Relaxing the preflight would change the checks behind the published Windows measurements. A platform branch changes only where scratch databases live.

## Consequences

Linux and macOS skip the RAM and disk budget checks and the Python and SQLite version pins, which ADR-0003 imposes for the Windows measurements. Measurements from those platforms are timing evidence only and must not be mixed with the Windows table. The load benchmark remains Windows-only.

## Revisit when

A Linux or macOS resource budget should be enforced, or the load benchmark gains a portable memory sampler.

## Validation plan

Run `make test` and each drill (`history`, `publish`, `restart`) on Linux and macOS, and confirm the Windows run still passes unchanged.

## Outcome

Archived portability transcripts cover four environments. [Windows laptop](../evidence/adr-0005-windows.txt) · [Ubuntu](../evidence/adr-0005-ubuntu.txt) · [macOS](../evidence/adr-0005-macos.txt) · [Linux container](../evidence/adr-0005-container.txt)

[MEASURED – Windows laptop build 26300, Python 3.10.11, SQLite 3.40.1, 27 November 2026] The four Make targets (docs-check, docs-test, verify, test) and the history, publish and restart drills exited 0. The unit suite ran 32 tests. This was a local laptop run. [Archived Windows command output](../evidence/adr-0005-windows.txt) [Windows validation record in PR #1](https://github.com/puni344/earthquake-catalog-backfill/pull/1)

[MEASURED – GitHub-hosted runners, 27 November 2026] Both native jobs ran `make verify`, `make test` (32 tests OK) and the history, publish and restart drills. The container job built the image and ran the default verifier with networking disabled. The push and PR runs each passed. [Ubuntu](../evidence/adr-0005-ubuntu.txt) · [macOS](../evidence/adr-0005-macos.txt) · [Linux container](../evidence/adr-0005-container.txt) · [Push run](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970108628) · [PR run](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970120016)

| Machine | Python | SQLite | Push job | PR job |
|---|---|---|---|---|
| [Native Ubuntu, Linux x86_64](../evidence/adr-0005-ubuntu.txt) | 3.15.2 | 3.46.1 | [PASS](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970108628/job/140408186011) | [PASS](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970120016/job/140408221502) |
| [Native macOS, Darwin arm64](../evidence/adr-0005-macos.txt) | 3.15.2 | 3.53.4 | [PASS](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970108628/job/140408185986) | [PASS](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970120016/job/140408220824) |
| [Docker on Ubuntu, Linux x86_64](../evidence/adr-0005-container.txt) | 3.11.14 | 3.40.1 | [PASS](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970108628/job/140408185707) | [PASS](https://github.com/puni344/earthquake-catalog-backfill/actions/runs/45970120016/job/140408221357) |
