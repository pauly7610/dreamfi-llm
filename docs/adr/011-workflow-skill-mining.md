# ADR 011: Workflow Traces Create Reviewed Skill Candidates

## Status

Accepted.

## Context

DreamFi needs a way to learn repeatable expert workflows without bloating prompt
context or turning every connector into an always-loaded skill. Users also need
to trust that the system is not silently creating production behavior from raw
activity logs.

The product idea is simple: when a teammate repeatedly solves the same kind of
problem with the same sources, identifiers, checks, and review edits, DreamFi
should be able to package that pattern as a candidate skill.

## Decision

DreamFi records workflow traces and mines repeated non-private traces into
`SkillCandidate` rows.

The system stores a redacted starter-question pattern and hash, not the raw
starter question. Candidate generation produces reviewable contracts:

- intent summary
- required inputs
- source contract
- tool plan
- freshness contract
- answer contract
- refusal rules
- eval seed cases

Candidate approval does not mutate the active skill registry and does not edit
locked `evals/` files. A real skill still requires an explicit PR.

## Consequences

Good:

- repeated expert work becomes visible and reviewable
- context stays lean because candidates are proposed after repeated use
- fintech operational workflows can carry explicit freshness and refusal rules
- the system can learn from human edits without storing raw starter questions

Tradeoffs:

- there is one more review queue to manage
- candidates are not automatically runnable skills
- the Go service does not yet expose this learning path

## Follow-Up

- Add a console review surface for skill candidates.
- Define the approved-candidate-to-skill-PR checklist.
- Add runtime freshness contracts before shipping operational skills that rely
  on NetXD, Sardine, or Socure exact-record reads.
