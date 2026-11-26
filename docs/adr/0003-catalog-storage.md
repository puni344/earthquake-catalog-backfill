# ADR-0003 · Publish named generations with Python and local SQLite transactions

Status: Accepted

Date / proposed by: 25 November 2026 / Codex

Accepted by: puni344 on 25 November 2026

Reversibility: two-way door. Rebuild the local index from frozen inputs to switch stores.

## Context

One writer must survive a process kill while readers inspect a complete named publication. The measured runtime is CPython 3.10.11 with SQLite 3.40.1. OneDrive is present in the workspace path. See the [design and measured constraints](../design/DESIGN-DOC.md).

## Decision drivers

Atomic recovery 45%, inspectable history 30%, setup and memory 25%.

## Options considered and comparison matrix

[ESTIMATE – paper evaluation on a 1–5 scale, higher is better] Columns follow the driver order above. Alternatives have not been benchmarked.

| Option | First driver | Second driver | Third driver |
|---|---|---|---|
| Flat JSON plus rename | 3 · single file replace | 2 · manual indexes | 5 · minimal install |
| PostgreSQL in Docker | 5 · transaction support | 5 · SQL joins | 2 · daemon and second service |
| Python stdlib and SQLite | 5 · one writer transaction | 5 · SQL joins | 5 · installed runtime |

## Decision

Use native Python 3.10.11, bundled SQLite 3.40.1 and a CLI. Keep raw blobs immutable, store checkpoint and row mutations together, and publish generations with a transactional pointer. Keep runtime state on local unsynced disk.

## Why each alternative was rejected

A flat file works for one manifest but joining per-event history across generations requires a second indexing and consistency mechanism. PostgreSQL offers multi-writer operation that the single-writer workload does not require, and Docker was initially stopped on this machine.

## Consequences

A single-file database supports offline review and limits parallel writes. Raw files and database metadata have separate durability boundaries. Validate hashes and tolerate orphan blobs during recovery. Process-kill evidence covers application crash recovery only.

## Revisit when

Two writers become necessary or measured reader stalls prevent sampling across the crash boundary. Revisit runtime pin before network-facing deployment.

## Validation plan

Run `python -m earthquake.verify --drill publish` with concurrent readers. For each successful read, record its timestamp, publication ID and a digest computed in deterministic order from the actual returned rows. Compare the digest with the independent expected digest for that same ID. Require observed reads before the kill, during interruption and after recovery. Record read errors and recovery time, then query both publications by ID again and verify their returned rows. Save observations and timing in `docs/evidence/quake-publish.txt`.

## Outcome

[MEASURED – Windows laptop, 26 November 2026] M01 verified both accepted pins in the executing interpreter and reopened a committed SQLite row under the resolved local state directory. [Preflight evidence](../evidence/M01-preflight.txt)

[MEASURED – M04, 26 November 2026] Each window transaction binds its checkpoint to the canonical fixture manifest digest, UTC window start date and source body SHA-256. The pre-commit kill rolled back both rows and checkpoint. The post-commit kill preserved both before acknowledgment. Verification covers forced ingestion-worker termination on this Windows laptop. Power-loss and disk-failure durability are unverified. [Crash transcript](../evidence/M04-restart.txt)

[MEASURED – M05, 26 November 2026] Fresh reader processes retrieved the 1,090-row earlier and 2,569-row current publications. A missing daily checkpoint and altered staging values each blocked publication while the earlier extract remained current. [History and failure tests](../evidence/M05-history.txt)

[MEASURED – M06, 26 November 2026] After the uncommitted pointer update, all four readers completed old-publication reads, then repeated them after the publisher exited. After retry committed, fresh reads returned the seven-day publication. All 36 current observations and both final named lookups matched the independently expected row digest for the reported ID. [Publisher crash proof](../evidence/quake-publish.txt). The [intake evidence](../evidence/quake-machine.txt) and [source spike](../evidence/quake-detail.txt) establish prerequisites only.

M08 passed on 26 November 2026. Readers observed the three-day publication during the ingestion outage and the week after commit. Both named publications returned their original scoped digests. [Integrated verification](../evidence/quake-verify.txt)
