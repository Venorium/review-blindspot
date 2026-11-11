"""Descriptive metrics with explicit denominators and clustered comparisons."""
from __future__ import annotations
from collections import defaultdict
from itertools import combinations
import random
from statistics import mean


def rate(n: int | float, d: int) -> float | None:
    return n / d if d else None

def target_state(row: dict) -> int | None:
    """1=adjudicated target detection, 0=target missed, None=not established."""
    if row["variant"] != "faulty":
        return None
    sub = row.get("submission")
    if not sub or sub["execution"]["status"] != "ok":
        return None
    verdict = sub["review"]["verdict"]
    if verdict == "approve":
        return 0
    if verdict == "abstain":
        return None
    annotation = row.get("annotation")
    if annotation is None:
        return None
    return {"detected": 1, "missed": 0}.get(annotation["target_detection"])

def outcome(rows: list[dict]) -> dict:
    decisions = []
    for row in rows:
        sub = row.get("submission")
        decisions.append(sub["review"]["verdict"] if sub and sub["execution"]["status"] == "ok" else None)
    gate = ("reject" if "request_changes" in decisions else
            "approve" if all(d == "approve" for d in decisions) else "unresolved")
    complete = all(d in ("approve", "request_changes") for d in decisions)
    states = [target_state(row) for row in rows]
    target = ("detected" if 1 in states else "missed" if all(s == 0 for s in states) else "unresolved")
    first = rows[0]
    return {key: first[key] for key in ("arm_id", "case_id", "family_id", "variant", "repeat")} | {
        "gate": gate, "complete_decisive": complete,
        "target": target if first["variant"] == "faulty" else "not_applicable",
        "reviewer_count": len(rows)}

def bootstrap_family_delta(deltas: dict[str, list[float]], *, draws: int = 2000, seed: int = 42) -> dict:
    values = [mean(v) for _, v in sorted(deltas.items()) if v]
    n = len(values)
    result = {"family_count": n, "mean_delta": mean(values) if n else None,
              "bootstrap_percentile_95": None,
              "unit": "family; repeats averaged within family; paired arms retained",
              "warning": "Exploratory percentile interval; small family counts and selected complete cases limit inference."}
    if n < 2:
        return result
    rng = random.Random(seed)
    estimates = sorted(mean(rng.choices(values, k=n)) for _ in range(draws))
    def quantile(p: float) -> float:
        x = p * (len(estimates) - 1)
        lo = int(x)
        hi = min(lo + 1, len(estimates) - 1)
        return estimates[lo] + (x - lo) * (estimates[hi] - estimates[lo])
    result["bootstrap_percentile_95"] = [quantile(0.025), quantile(0.975)]
    return result

def joint_misses(rows: list[dict]) -> list[dict]:
    """Pooled descriptive excess joint misses, not a causal independence test."""
    by_arm = defaultdict(lambda: defaultdict(dict))
    for row in rows:
        if row["variant"] == "faulty":
            by_arm[row["arm_id"]][(row["case_id"], row["repeat"])][row["slot"]] = target_state(row)
    results = []
    for arm, groups in sorted(by_arm.items()):
        slots = sorted({s for group in groups.values() for s in group})
        for a, b in combinations(slots, 2):
            paired = [(g.get(a), g.get(b)) for g in groups.values() if g.get(a) is not None and g.get(b) is not None]
            n = len(paired)
            pa = rate(sum(x == 0 for x, _ in paired), n)
            pb = rate(sum(y == 0 for _, y in paired), n)
            joint = rate(sum(x == 0 and y == 0 for x, y in paired), n)
            reference = pa * pb if n else None
            results.append({"arm_id": arm, "slots": [a, b], "paired_known_trials": n,
                            "missing_or_ungraded_pairs": len(groups) - n,
                            "miss_rate_a": pa, "miss_rate_b": pb, "joint_miss_rate": joint,
                            "product_of_pooled_marginals": reference,
                            "excess_joint_miss": joint - reference if n else None,
                            "warning": "Shared item difficulty alone can produce positive pooled excess; no causal correlation claim."})
    return results

def summarize(rows: list[dict], mode: str) -> dict:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["arm_id"], row["case_id"], row["variant"], row["repeat"])].append(row)
    groups = [outcome(grouped[k]) for k in sorted(grouped)]
    arms = []
    for arm in sorted({g["arm_id"] for g in groups}):
        ag = [g for g in groups if g["arm_id"] == arm]
        faulty = [g for g in ag if g["variant"] == "faulty"]
        clean = [g for g in ag if g["variant"] == "correct"]
        f_n, c_n = len(faulty), len(clean)
        approvals = sum(g["gate"] == "approve" for g in faulty)
        unresolved = sum(g["gate"] == "unresolved" for g in faulty)
        complete = [g for g in faulty if g["complete_decisive"]]
        clean_reject = sum(g["gate"] == "reject" for g in clean)
        clean_unknown = sum(g["gate"] == "unresolved" for g in clean)
        detected = sum(g["target"] == "detected" for g in faulty)
        missed = sum(g["target"] == "missed" for g in faulty)
        unknown = f_n - detected - missed
        ar = [r for r in rows if r["arm_id"] == arm]
        statuses = defaultdict(int)
        for row in ar:
            statuses[row["submission"]["execution"]["status"] if row.get("submission") else "missing"] += 1
        usage = {}
        for label in ("input_tokens", "output_tokens", "cost_usd", "latency_seconds"):
            known = [r["submission"]["execution"][label] for r in ar
                     if r.get("submission") and r["submission"]["execution"][label] is not None]
            usage[label] = {"known_sum": sum(known) if known else None, "known_jobs": len(known),
                            "unknown_jobs": len(ar) - len(known)}
        arms.append({"arm_id": arm, "faulty_groups": f_n, "control_groups": c_n,
                     "review_jobs": len(ar), "execution_status_counts": dict(statuses),
                     "faulty_approved_groups": approvals, "faulty_unresolved_gate_groups": unresolved,
                     "unsafe_approval_bounds_all_scheduled": [rate(approvals, f_n), rate(approvals + unresolved, f_n)],
                     "complete_faulty_groups": len(complete),
                     "unsafe_approval_rate_complete": rate(sum(g["gate"] == "approve" for g in complete), len(complete)),
                     "control_rejection_bounds_all_scheduled": [rate(clean_reject, c_n), rate(clean_reject + clean_unknown, c_n)],
                     "control_rejected_groups": clean_reject,
                     "target_detected_groups": detected, "target_missed_by_all_groups": missed,
                     "target_unresolved_groups": unknown,
                     "target_recall_bounds": [rate(detected, f_n), rate(detected + unknown, f_n)],
                     "common_target_miss_bounds": [rate(missed, f_n), rate(missed + unknown, f_n)],
                     "unique_cases_with_target_detected": len({g["case_id"] for g in faulty if g["target"] == "detected"}),
                     "unattested_or_missing_isolation_jobs": sum(not r.get("submission") or not r["submission"]["execution"]["isolation_attested"] for r in ar),
                     "usage": usage})
    comparisons = []
    names = {a["arm_id"] for a in arms}
    for treatment, baseline in [("panel_informed", "panel_blind"), ("panel_blind", "solo_budget"), ("panel_blind", "solo_blind"), ("panel_mixed", "panel_blind")]:
        if treatment not in names or baseline not in names:
            continue
        a = {(g["case_id"], g["repeat"]): g for g in groups if g["arm_id"] == treatment and g["variant"] == "faulty"}
        b = {(g["case_id"], g["repeat"]): g for g in groups if g["arm_id"] == baseline and g["variant"] == "faulty"}
        deltas = defaultdict(list)
        eligible = 0
        for key in a.keys() & b.keys():
            if a[key]["complete_decisive"] and b[key]["complete_decisive"]:
                deltas[a[key]["family_id"]].append(float(a[key]["gate"] == "approve") - float(b[key]["gate"] == "approve"))
                eligible += 1
        comparisons.append({"treatment_minus_baseline": treatment + " - " + baseline,
                            "metric": "unsafe approval; positive means treatment worse",
                            "eligible_case_repeat_pairs": eligible,
                            "excluded_case_repeat_pairs": len(a.keys() | b.keys()) - eligible,
                            **bootstrap_family_delta(deltas)})
    identity_registry = defaultdict(set)
    exceeded_caps = []
    for row in rows:
        sub = row.get("submission")
        if not sub:
            continue
        ex = sub["execution"]
        if "model_key" in row and ex.get("model_id") and ex.get("harness_id"):
            identity_registry[row["model_key"]].add((ex["model_id"], ex["harness_id"]))
        cap = row.get("output_token_cap")
        observed = ex.get("output_tokens")
        if cap is not None and observed is not None and observed > cap:
            exceeded_caps.append(row.get("job_id"))
    identity_audit = [{"model_key": key, "observed_model_and_harness_ids": sorted(value),
                       "multiple_identities": len(value) > 1} for key, value in sorted(identity_registry.items())]
    return {"identity_audit": identity_audit, "observed_output_cap_exceeded_jobs": exceeded_caps,
            "mode": mode, "results_are_model_evidence": False if mode.startswith("SYNTHETIC") else "NOT_AUTOMATICALLY_VALIDATED",
            "warnings": ["Bundled cases are synthetic development fixtures, not a held-out natural benchmark.",
                         "Operational rejection is not target-defect detection. Control rejection is not fully adjudicated false-positive precision.",
                         "Unknown/error/abstain outcomes are never approval; bounds expose their effect.",
                         "Pair/family, not reviewer invocation, is the independent sampling unit.",
                         "No assertion of model superiority or equal actual cost follows from output caps."],
            "arms": arms, "paired_comparisons": comparisons, "pairwise_joint_misses": joint_misses(rows), "groups": groups}
