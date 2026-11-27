# ADR-0007 · Local evidence for measured claims

Status: Proposed
Date / proposed by: 27 November 2026 / Codex
Accepted by: Pending review
Reversibility: two-way door. The check reads Markdown and can be changed independently of the verifier.

## Context

A reviewer should be able to open the supporting artifact from a measured claim in an offline checkout. Hosted job logs can expire.

## Decision drivers

Preserve measurements, identify unsupported claims by file and line, and use the existing Python runtime.

## Options considered and comparison matrix

| Approach | Finds unsupported claims | Works offline |
|---|---|---|
| Ordinary link checker | Only detects broken links that are present | Yes |
| Tagged-claim checker | Requires a local evidence citation for each tag | Yes |
| Check hosted URLs | Checks reachability on the day of review | No |

## Decision

Run `make evidence-check` locally and in documentation CI. It scans README.md and all Markdown files recursively under docs. Use the uppercase `[MEASURED ...]` marker and an inline Markdown link on the tag or after it in the same paragraph, list item or table row. Wrapped prose may continue onto the next line. The next tag begins a new claim. The resolved link must name a file under docs/evidence or docs/benchmarks. Code samples are excluded.

## Why each alternative was rejected

A valid link to a PR can outlive the job output it cites. A document with no links at all can pass ordinary link checking.

## Consequences

The checker reports every unsupported tag with its source location and exits nonzero. Reviewers still need to inspect the cited artifact to confirm the number, machine and workload.

## Revisit when

The documentation moves claims into a different directory or adopts a different citation format.

## Validation plan

Exercise linked and unsupported claims in disposable documents. Run the repository check alongside the documentation checker and the offline verifier.

## Outcome

[MEASURED – Windows laptop, 27 November 2026] The initial repository scan found 16 tagged claims with qualifying local files. The passing and failing fixture tests passed. [Command output](../evidence/task-2-evidence-check.txt) · [Test fixtures](../../earthquake/test_evidence.py)
