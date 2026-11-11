# Review Blind Spot — experiment report

**EXTERNAL_REVIEWS_UNVERIFIED**

> **Unverified external reviews.** Complete records do not certify scientific validity.

## At a glance

| Protocol | Faulty approvals | Target recall | Control rejection |
| --- | --- | --- | --- |
| panel\_blind | 0/10 observed; 0.0% | 10/10 detected; 100.0% | 3/10 rejected; 30.0% |
| panel\_informed | 0/10 observed; 0.0% | 10/10 detected; 100.0% | 3/10 rejected; 30.0% to 40.0% |
| panel\_mixed | 0/10 observed; 0.0% | 10/10 detected; 100.0% | 0/10 rejected; 0.0% to 30.0% |
| solo\_blind | 0/10 observed; 0.0% | 10/10 detected; 100.0% | 1/10 rejected; 10.0% to 20.0% |

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

Scheduled: 10 faulty groups, 10 controls; 60 reviewer jobs.
Faulty approvals: 0; possible unsafe-approval fraction: 0.0% to 0.0%.
Complete decisive faulty groups: 10; approval fraction on this selected subset: 0.0%.
Adjudicated target-recall bounds: 100.0% to 100.0%; unresolved target groups: 0.
Rejection fraction for controls: 30.0% to 30.0%. This is not adjudicated finding-level false-positive precision.
Execution status counts: {'ok': 59, 'invalid_output': 1}.
Reported cost: unknown across 0 known jobs; 60 unknown.

### panel_informed

Scheduled: 10 faulty groups, 10 controls; 60 reviewer jobs.
Faulty approvals: 0; possible unsafe-approval fraction: 0.0% to 0.0%.
Complete decisive faulty groups: 10; approval fraction on this selected subset: 0.0%.
Adjudicated target-recall bounds: 100.0% to 100.0%; unresolved target groups: 0.
Rejection fraction for controls: 30.0% to 40.0%. This is not adjudicated finding-level false-positive precision.
Execution status counts: {'ok': 57, 'invalid_output': 3}.
Reported cost: unknown across 0 known jobs; 60 unknown.

### panel_mixed

Scheduled: 10 faulty groups, 10 controls; 60 reviewer jobs.
Faulty approvals: 0; possible unsafe-approval fraction: 0.0% to 0.0%.
Complete decisive faulty groups: 10; approval fraction on this selected subset: 0.0%.
Adjudicated target-recall bounds: 100.0% to 100.0%; unresolved target groups: 0.
Rejection fraction for controls: 0.0% to 30.0%. This is not adjudicated finding-level false-positive precision.
Execution status counts: {'ok': 56, 'invalid_output': 4}.
Reported cost: unknown across 0 known jobs; 60 unknown.

### solo_blind

Scheduled: 10 faulty groups, 10 controls; 20 reviewer jobs.
Faulty approvals: 0; possible unsafe-approval fraction: 0.0% to 0.0%.
Complete decisive faulty groups: 10; approval fraction on this selected subset: 0.0%.
Adjudicated target-recall bounds: 100.0% to 100.0%; unresolved target groups: 0.
Rejection fraction for controls: 10.0% to 20.0%. This is not adjudicated finding-level false-positive precision.
Execution status counts: {'ok': 19, 'invalid_output': 1}.
Reported cost: unknown across 0 known jobs; 20 unknown.

## Paired comparisons

Exploratory family-cluster bootstrap; missing outcomes excluded here remain visible in the bounds above.

- panel_informed - panel_blind: delta 0.0, 95% percentile interval [0.0, 0.0]; 10 families, 0 excluded pairs.
- panel_blind - solo_blind: delta 0.0, 95% percentile interval [0.0, 0.0]; 10 families, 0 excluded pairs.
- panel_mixed - panel_blind: delta 0.0, 95% percentile interval [0.0, 0.0]; 10 families, 0 excluded pairs.

## Shared misses between reviewers

For each pair of reviewer slots in an arm, on the faulty candidates where both outcomes are known: how often each missed the target, how often both did, and the product of the two miss rates. Shared item difficulty alone can push the joint rate above the product; this describes, it does not test dependence.

| Arm | Slots | Known pairs | Miss A | Miss B | Both missed | Product | Excess |
| --- | --- | --- | --- | --- | --- | --- | --- |
| panel\_blind | r1 / r2 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_blind | r1 / r3 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_blind | r2 / r3 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_informed | r1 / r2 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_informed | r1 / r3 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_informed | r2 / r3 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_mixed | r1 / r2 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_mixed | r1 / r3 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |
| panel\_mixed | r2 / r3 | 10 | 0.0% | 0.0% | 0.0% | 0.0% | +0.0 pts |

## Required before a public empirical claim

Independent corpus audit, resolved model/settings identities, verified review isolation, frozen protocol, adjudication audit, actual cost accounting, and a new held-out corpus.
