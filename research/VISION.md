# Intent, relevance and impact

## Core question

The number of reviewers is not the main object of study. The object is the structure of
information and decisions: who sees the contract, the patch, the author's account, the
other reviewers' outputs, and which evidence conditions the final decision? The project
makes that structure explicit, controllable and measurable.

Starting question: for the same code and the same accessible specification, which
protocol gives the best trade-off between faulty approvals, identified defects, rejected
controls and resources consumed? Two models can disagree without either identifying the
fault; three agreements can certify nothing. These are possibilities to test, not results.

## Intended value

For an applied research team: a reusable protocol, audited cases, a clearly defined
failure signal and falsifiable experiments. For a tooling team: a test bench for review
configurations that does not reward a tool simply because it rejects everything. For an
architect: a way to justify the number of reviewers, their context and the merge rule
with evidence rather than intuition.

External work is listed in [RELATED_WORK.md](RELATED_WORK.md). It motivates a reliability
study but establishes neither the novelty of this repository nor the behaviour of the
models tested here. The closely related work by Zietsman [S2] means the project should be
treated as a possible controlled extension or replication, not as the first discovery of
shared errors in AI review.

## What would make the project useful

A result should change a decision. Hypothetical examples of useful results: "on a
preregistered external set, the panel improves recall but the gain disappears at equal
total cost", or "removing the author's comment changes the approval rate, with documented
uncertainty and limits". A null result can be useful if it invalidates a costly practice.
A single spectacular failure is a counterexample; it does not measure a frequency.

A third party should be able to recompute every metric from the raw records and swap
providers without rewriting the experiment. A team that uses the protocol, or properly
contests a case, is a stronger signal of usefulness than a decorative demonstration.
No star count is a scientific objective.

## Differentiation to establish, not to proclaim

The core combines paired control and faulty variants, constant information across
conditions, reviews without shared outputs, a better-resourced solo baseline, a judgment
of the defect actually identified that is separate from the verdict, and visible missing
data. Each technique exists elsewhere. Any new value lies in testing them together and in
their usability, after comparison with existing work.

Out of scope: a complete review product, model training, every language and tool at once,
and a public leaderboard. The first scope is Python, a file interface and one clear
experiment. Multi-file changes and other languages come after the instrument is valid.

## Why the first cases are simple

They exist to expose errors in the judge, the packets or the formulas. Advanced models may
well identify every defect; that is a normal control result, never a reason to hide
numbers. Harder realistic cases must be selected before seeing scores, and specifications
must never be made artificially ambiguous to manufacture failures.
