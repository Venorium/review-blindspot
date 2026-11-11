# Experimental protocol v0.1

**Status: starting protocol, not preregistered with a third party.** The file
`configs/extended.DRAFT.json` is an example of an extended plan, neither an authorization
nor a recommendation to run all of its calls.

## 1. Question and hypotheses

Proposed primary question: with the specification and candidate held constant, does the
author's comment change the faulty approvals of a three-reviewer panel? Proposed primary
comparison: `panel_informed - panel_blind`. No direction is assumed: the comment may help,
hurt or change nothing.

Secondary question: does a blind panel improve on a solo reviewer given a comparable total
output cap (`panel_blind - solo_budget`)? `solo_blind` measures the cost of adding reads
relative to a single reviewer, not a collective effect at constant budget. `panel_mixed` is
an exploratory extension: it mixes the effects of diversity, individual skill and
provider, and on its own does not identify a causal effect of diversity.

Before a campaign, choose a single primary comparison, a primary metric and a practically
useful effect size. Never move that choice after reading results. The text-only track
evaluates neither a tool-using agent nor a complete review product.

## 2. Implemented arms

| Arm | Sessions per candidate | Author comment | Output cap per session |
|---|---:|---|---:|
| solo_blind | 1, logical model A | no | 1,000 |
| solo_budget | 1, logical model A | no | 3,000 |
| panel_blind | 3, logical model A | no | 1,000 |
| panel_informed | 3, logical model A | yes | 1,000 |
| panel_mixed (extension) | 3, A/B/C | no | 1,000 |

These numbers are proposed parameters; each configuration sets its own. A transport must
verify that the provider supports and enforces them. Count separately repeated inputs,
outputs, billed reasoning tokens, caches, failed calls and latency. Three calls of 1,000
tokens do not necessarily cost the same as one call of 3,000; a panel's latency is not the
sum of its latencies when calls run in parallel. Reports give observed sums, not the
wall-clock latency of a panel.

Do not infer model identities from imprecise marketing names. Record the identifier
actually returned, provider, client or harness version, parameters, alias resolution and
date. Changing a model or setting during a campaign requires a new identified block.

## 3. Unit and randomization

A pair is a base, a variant conforming to the controls, and a variant with a verifiable
target defect. Both variants keep exactly the same contract. A panel trial contains all
planned slots for one candidate, arm and repetition. The clustering unit is the original
case family: variants, repetitions and slots stay together. Each bundled case is its own
family; derived variants or close cases must be regrouped before freezing. A defect shared
by several methods does not create several independent observations.

Job order is shuffled with a recorded seed. Job identifiers are random and opaque; their
reproducibility rests on the retained manifest, not on regenerating the same identifiers.
The order actually executed is logged by the transport. Interleaving arms avoids
confounding an arm with an outage period or a provider update.

Repeating calls can estimate a model's variability; it does not increase the number of
independent problems. A deterministic model repeated without variation may return the
same answer; such repetitions are not independent evidence.

## 4. Information and blinding boundaries

Every reviewer sees SPEC.md, before.py, candidate.py, patch.diff and test_public.py. Only
the informed arm sees AUTHOR_NOTE.md. No reviewer sees the witness tests, the internal case
name, the alternative variant, peer outputs or any repository file. Author notes are
plausible intentions, identical for both variants of a pair; they are not false claims
about test results.

This intervention measures the addition of that comment, with its length and content. On
its own it does not demonstrate anchoring or authority bias. Isolating those mechanisms
needs a preregistered neutral control of comparable length and a factorial content/source
design, which is not implemented and must not be improvised after scores.

The specification contains every rule that is evaluated. Witness tests check consequences
of that contract, not hidden conventions. Removing a requirement and then blaming the
reviewer for missing it is a different, potentially unidentifiable experiment.

Packets are separated by files, but that separation is not operating-system security. A
reviewer must run in a clean session and environment, without access to the repository,
the manifest, peer folders, the home directory, memory or connectors, and without the
builder's history. In text-only mode, sending exactly the allowed bytes in a request with
no tools and no conversational memory is an auditable operating mode; a stored attestation
does not prove it happened.

## 5. Ground truth and judgment

For each pair, the control must pass the public and witness tests; the faulty candidate
must pass the public tests and fail at least one witness by assertion. A syntax error,
import error, skip or timeout is not a validated target defect. The base passes the public
examples; it may already contain the problem the change was meant to fix, so the corpus
mixes incomplete fixes and regressions.

A witness proves its counterexample exists, not that the specification is exhaustive.
The control is not "mathematically bug-free". New observations on a control must be
triaged before any metric is called a false positive.

A request for changes does not prove that the target defect was detected. A separate
judgment links findings to the mechanism, a valid input or state, and the violated
requirement. It concludes detected, missed or undetermined. Grading packets hide model and
arm; the judge receives the candidate, contract, target, witness and review. See
[ADJUDICATION.md](ADJUDICATION.md). Keyword or line matching is never the sole judge.

## 6. Measures and denominators

Initial merge rule: **any-block**. A single `request_changes` blocks the candidate. The
group approves only if every planned slot returns `approve`. Without a block, a missing
answer, timeout or `abstain` leaves the group undetermined. A group can be blocked but
incomplete; that difference is kept. Majority voting and a final judge are different
experiments, not options to mix into the same metric.

**Faulty approval.** Over the planned faulty groups, the share approved unanimously. The
program reports the observed lower bound A/N and the upper bound (A+U)/N, where U is the
undetermined groups that could still approve. These are missing-data bounds, not
confidence intervals. The rate over complete groups only is shown separately and can be
biased by selecting successful trials.

**Control rejection.** Share of controls blocked by at least one reviewer, with analogous
bounds. This is not reported as finding precision: signals that might reveal a real
defect in the control must also be judged.

**Target detection.** A group detects when at least one finding is judged to identify the
target. A rejection for another reason does not count. An approval without findings is a
missed target; a missing or ambiguous annotation stays unknown. Recall and misses shared
by all reviewers are bounded while keeping these unknowns.

**Joint misses.** For two slots, compute on the same annotated faulty trials P(Mi), P(Mj)
and P(Mi and Mj). Show the product of marginals and the absolute excess. Even with
conditionally independent outputs, variation in difficulty across cases can produce a
positive excess when everything is pooled. This descriptive table is neither proof of
causality nor a pure measure of conditional dependence.

**Costs.** Never convert unknown usage to zero. Reports give the known sum and the number
of reported and unknown jobs, including failed calls. Cost per additional defect must use
comparable units, with judging costs visible, not a total of repeated detections presented
as distinct bugs.

## 7. Uncertainty and statistical limits

The harness computes paired approval differences on complete pairs, clusters repetitions
at the family level, then uses a family percentile bootstrap (2,000 resamples, fixed seed)
that keeps arms paired. It is exploratory: with few small families, intervals can be
coarse or degenerate, and independence between synthetic families is itself an assumption.
Never read a zero-width interval as certainty.

No improvised multiple significance tests. For a confirmatory publication, choose the
inference method after the pilot but before the holdout, justify sample size by simulation
adapted to the smallest useful effect and the dependence structure, then freeze the plan.
More distinct problems matter more than excessive repetition of the same cases. Keep the
development set out of final conclusions.

## 8. Freezing, incidents and reproducibility

`prepare` freezes configuration, harness code, prompts, schemas, corpus and research
documents in the assessor folder. The manifest holds their hashes and the Python
environment. Responses and annotations are added once with a hash; reports are snapshots
that are never overwritten. Checksums detect accidental change, not an administrator who
rewrites both data and hashes.

First attempts are kept. The transport never retries silently; an interrupted attempt is
re-sent only on explicit request and recorded as a new numbered attempt. A malformed JSON
answer is an incident, not an invitation to ask the same model to think harder without
counting it.

Keep the raw data actually exposed by the tool, transport metadata, parameters, timestamps
and billing. Do not ask for hidden internal reasoning. Canonical import JSON does not
replace archiving the raw transport.

## 9. Minimum conditions for an interpretable result

Audited contracts, independently reviewed witnesses, negative controls, verified
information boundaries, resolved models and parameters, genuinely comparable arms,
visible failures, calibrated judging, fresh held-out data, traceable costs and a hypothesis
stated in advance. Anything missing must appear as a limitation, never be replaced by a
more convincing presentation.
