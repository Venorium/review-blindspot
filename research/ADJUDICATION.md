# Judging a review without confusing verdict and understanding

## Two different truths

Witness tests establish that a candidate violates a contract on some input. An annotation
establishes that a specific finding actually identified that violation. The second is not
automatic: the text may describe another fault, an out-of-domain assumption, or a correct
line with incorrect reasoning.

An `approve` verdict has no blocking finding, so it is inferred as a missed target. A
`request_changes` must be annotated. `abstain`, errors and ambiguous annotations are never
converted into certain non-detection; they stay unknown within the bounds.

## Rubric

**Detected:** same causal mechanism as the target defect, an input or state inside the
contract, the correct consequence, and an identified finding. A vague label such as "check
the boundary" is not enough when several mechanisms are possible. The judge cites a trigger
or requirement so the decision can be audited.

**Missed:** the finding does not describe the target, even if the candidate is blocked.
Another real fault is worth recording separately; it is never renamed as the target.

**Unresolved:** the evidence or the match is insufficient. Ask for a second annotation
rather than forcing a favourable label.

**Control:** the target is `not_applicable`. Every rejection should still be triaged: false
alarm, real defect found, specification ambiguity, or corpus problem. The rationale field
carries that triage; no per-finding precision score is computed yet.

## Procedure

Export grading packets with `rbs grading-packets`; they contain neither the model identity
nor the arm. Two genuinely separate judges can annotate them; keep their versions outside
the run, measure agreement and import one resolved adjudication with the announced
procedure. A single judgment is never "double-blind". An LLM judge must be calibrated
against annotations reviewed by a competent person.

`annotation.TEMPLATE.json` binds the annotation to the response hash. Replace placeholder
fields, write a short rationale and a consultable reference. The reference is documentary;
the program neither executes nor certifies it. A counterexample supplied by an agent is
untrusted code. `rbs adjudicate` accepts one JSON file or a JSONL batch, validated in full
before anything is stored.

## Contested corpus

Open a contestation record with the case, version, disputed rule and witness. Before a
freeze: fix, then re-verify both variants. After a freeze: never silently change the
run's oracle. Publish the incident, keep the original analysis next to a clearly separate
sensitivity analysis, and create the next corpus version. Exclusion criteria must be
defined before knowing which arm wins.

## What is not measured here

No self-reported confidence is used as a calibrated probability. No Brier score, global
severity ranking or per-finding precision is provided without suitable annotations. A
defect in a change does not make every criticism of that change a true detection.
