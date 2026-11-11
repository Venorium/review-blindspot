# Related work (checked on 4 October 2026)

This targeted survey is not exhaustive. Links point to primary sources. Commercial claims
and authors' results are not results reproduced by this repository. No external corpus or
code was copied into the fixtures. Machine-readable list: [SOURCES.json](SOURCES.json).

## [S1] Martian — Code Review Bench

https://github.com/withmartian/code-review-benchmark

Provides data, judges and evaluation pipelines for code reviews, with offline and online
tracks. It is a direct neighbour to compare with and possibly integrate. Review Blind Spot
focuses on intervening on the protocol, with paired variants and executable controls,
rather than adding a tool leaderboard. That difference must be checked against a pinned
revision before any novelty claim.

## [S2] Christo Zietsman — The Specification as Quality Gate

https://arxiv.org/abs/2603.25773 (v1, 26 March 2026)

This preprint directly discusses shared errors in AI review and presents a small corpus of
planted bugs. The author describes the experiments as indicative, not a controlled
demonstration. It covers the central theme of this project. The extension pursued here
keeps the specification available to every reviewer, adds controls, separates verdict from
identified defect and accounts for resources. Its causal explanations about training data
are not reused without examination; they cannot be deduced from observed outputs alone.

## [S3] Anthropic — Demystifying evals for AI agents

https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents (9 January 2026)

Distinguishes trials, judges, traces and effective outcomes, and stresses including
negative cases. It motivates a harness that separates execution from judgment and final
state. This engineering guide does not establish that this protocol improves reviews.

## [S4] OpenAI — Introducing upgrades to Codex

https://openai.com/index/introducing-upgrades-to-codex/

Presents code-review capabilities and uses. A product source, not evidence of demand for
this repository.

## [S5] Agent Review Panel

https://github.com/wan-huiyan/agent-review-panel

Describes a workflow of reviewers, discussion and arbitration, a reminder that a
multi-agent panel is not new in itself. A transport could one day evaluate such a
protocol, treating its exchanges as a different intervention and making total compute
comparable.

## [S6–S7] CI actions

https://github.com/actions/checkout · https://github.com/actions/setup-python

The workflow pins both actions to verified commit SHAs, with read-only permissions and no
persisted credentials; Dependabot proposes updates.

## Open check

Refresh the survey on blind review, correlated errors, pull-request evaluations and
equal-budget comparisons. Identify the closest exact protocol, not just a similarly titled
paper, and record its version and consultation date. If the contribution is already
covered, prefer a replication, a new ablation or an upstream contribution over an
artificial novelty claim.
