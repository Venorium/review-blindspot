# Review Blind Spot — experiment report

**SYNTHETIC_DEMO_NOT_MODEL_RESULTS**

> **Scripted demonstration.** Answers and annotations were generated from known defects. No model was evaluated.

## At a glance

| Protocol | Faulty approvals | Target recall | Control rejection |
| --- | --- | --- | --- |
| panel\_blind | 0/2 observed; 0.0% | 1/2 detected; 50.0% | 1/2 rejected; 50.0% |
| solo\_blind | 1/2 observed; 50.0% | 0/2 detected; 0.0% | 1/2 rejected; 50.0% |

Counts use all scheduled groups. Ranges are missing-data bounds, **not confidence intervals**.

- **Faulty approvals:** a defective candidate passed the review gate.
- **Target recall:** a finding was separately adjudicated as identifying the target defect.
- **Control rejection:** a control candidate was blocked; this does not by itself prove a false positive.

**Read the three together.** Rejecting every candidate can remove faulty approvals while detecting no target defects. Check unresolved outcomes and actual resources before comparing protocols.

## Data quality signals

- Logical model keys with multiple reported model/harness identities: **0**.
- Jobs exceeding their declared output-token cap: **0**.
- Faulty groups with unresolved target detection: **0**.

These checks use reported metadata; zero alerts do not verify isolation, provider settings or equal cost.

## Validity boundaries

- Bundled cases are synthetic development fixtures, not a held-out natural benchmark.
- Operational rejection is not target-defect detection. Control rejection is not fully adjudicated false-positive precision.
- Unknown/error/abstain outcomes are never approval; bounds expose their effect.
- Pair/family, not reviewer invocation, is the independent sampling unit.
- No assertion of model superiority or equal actual cost follows from output caps.

## Per-arm outcomes

### panel_blind

Scheduled: 2 faulty groups, 2 controls; 12 reviewer jobs.
Faulty approvals: 0; possible unsafe-approval fraction: 0.0% to 0.0%.
Complete decisive faulty groups: 2; approval fraction on this selected subset: 0.0%.
Adjudicated target-recall bounds: 50.0% to 50.0%; unresolved target groups: 0.
Rejection fraction for controls: 50.0% to 50.0%. This is not adjudicated finding-level false-positive precision.
Execution status counts: {'ok': 12}.
Reported cost: 0 USD across 12 known jobs; 0 unknown.

### solo_blind

Scheduled: 2 faulty groups, 2 controls; 4 reviewer jobs.
Faulty approvals: 1; possible unsafe-approval fraction: 50.0% to 50.0%.
Complete decisive faulty groups: 2; approval fraction on this selected subset: 50.0%.
Adjudicated target-recall bounds: 0.0% to 0.0%; unresolved target groups: 0.
Rejection fraction for controls: 50.0% to 50.0%. This is not adjudicated finding-level false-positive precision.
Execution status counts: {'ok': 4}.
Reported cost: 0 USD across 4 known jobs; 0 unknown.

## Paired comparisons

Exploratory family-cluster bootstrap; missing outcomes excluded here remain visible in the bounds above.

- panel_blind - solo_blind: delta -0.5, 95% percentile interval [-1.0, 0.0]; 2 families, 0 excluded pairs.

Joint misses and their pooled-marginal reference are in metrics.json. Item difficulty confounds any causal interpretation.

## Required before a public empirical claim

Independent corpus audit, resolved model/settings identities, verified review isolation, frozen protocol, adjudication audit, actual cost accounting, and a new held-out corpus.
