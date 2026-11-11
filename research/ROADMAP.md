# Roadmap

One active ticket at a time; each ends with a test or an auditable artifact. Ticket IDs are
working names, not GitHub issues. The [changelog](../CHANGELOG.md) lists what shipped.

## Done

| Ticket | Result |
| --- | --- |
| RBS-001 | Independent reproduction of the starter and three refutation tests (`tests/test_protocol_refutations.py`) |
| RBS-002 | Real transport: `rbs review` for Ollama and stdin commands, twelve failure tests |
| RBS-006 | Pilots A and B: 500 local reviews with plans frozen before the first request ([results](../results/README.md)) |
| RBS-009 | One-command scripted demo, `python -m rbs quickstart` |
| RBS-010 | Read-only run diagnosis, `python -m rbs status` |
| RBS-011 | README presentation and readable report summary |
| RBS-012 | Report provenance: computing code versus code frozen in the run |
| RBS-013 | Agent Skill with evidence ledger and freshness check, installable as a Codex or Claude Code plugin |

## Next

**Human audit of judgments.** Have a competent person re-judge a random sample of the pilot
annotations blind to model and arm, measure agreement and publish disagreements. Until
then, every target judgment is an LLM judgment.

**Merge rule experiment.** Pilot B suggests that any-block panels multiply invented
objections on correct code. Preregister a comparison of any-block, majority, and "block
only with a reproducible counterexample executed in a sandbox", at equal resources, on
fresh cases. Acceptance: frozen plan, sandbox audited before any reviewer code runs.

**RBS-003 — Budget and incidents.** Add an explicit total budget and a multi-attempt log
before any campaign with retries. Reserve budget before a call and stop before exceeding
it; unknown prices mean no guarantee, never zero cost. Acceptance: timeout, invalid JSON,
provider refusal, missing usage and worker races covered; every attempt and its cost kept.

**RBS-004 — Audit of controls and judgment.** Have contracts and witnesses reviewed so
they never penalize an unstated rule. Add hard cases for the judge: right verdict with the
wrong reason, right mechanism with other wording, control with a plausible accusation.
Acceptance: independent double annotation on a small audited batch, with disagreements
handled explicitly. The builder cannot certify all of its own cases alone.

**RBS-007 — External set and holdout.** Prepare cases from real defects in projects with
compatible licenses, with provenance, frozen snapshots and a sufficient contract. Keep
families, variants and forks of one problem in the same split. Never run third-party pull
request code in the local trusted runner: sandbox first. Acceptance: predefined selection,
test data unused for tuning, size justified after the pilot, audited blind access, counted
preparation costs. Known public cases may be contaminated; calling them a holdout does not
prevent it.

**RBS-008 — Publication and replication.** Produce a short English report comparing with
the closest existing work on a pinned revision; provide scripts, shareable data and
failures. Acceptance: a third party reproduces the metrics without a provider account and
can attempt a new campaign with their own access.

## Criteria for changing course

If every model passes every case, keep that observation and move to realistic cases
selected before scoring; never obscure contracts. If a panel does not help at comparable
resources, publish the cost of that absence of gain. If an existing project already offers
the same instrument, prefer a compatible extension or an upstream contribution to a renamed
clone. If the judge is unreliable, improve the judge before increasing the number of calls.
