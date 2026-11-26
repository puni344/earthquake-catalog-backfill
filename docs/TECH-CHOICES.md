# Earthquake catalog technology choices

| Choice | Rationale and limit |
|---|---|
| Python standard library and SQLite | One local writer can commit rows and checkpoints together. Multiple simultaneous writers or measured reader stalls reopen the decision. [ADR-0003](adr/0003-catalog-storage.md) |
| Raw USGS responses plus hashes | Independent parent and daily requests let a reviewer inspect both sides of a disagreement and replay a frozen interval. [ADR-0002](adr/0002-catalog-acquisition.md) |
| Command-line interface | One offline demo must recover the extract and retrieve both publication IDs. [ADR-0001](adr/0001-catalog-structure.md) |
| GNU Make and standard-library Python for documentation | The Make target gives local review and CI the same entry point. A direct Python invocation is simpler for one person but does not exercise the shared build target. |
| GitHub Actions for documentation | A standard Ubuntu runner can check a public pull request independently. Running Make locally is sufficient for an unpublished checkout. The job checks repository visibility before allocating a runner. [Runner and cost decision](cost/COST.md) |
