from __future__ import annotations

from pathlib import Path
import argparse
import json

from data.gripper import Instance, feature_pool, planner, successors, test_instances, training_instances


def _valuation(feature, state) -> str:
    return "1" if feature.positive(state) else "0"


def _effect(feature, transition) -> str:
    before = feature.value(transition.source)
    after = feature.value(transition.target)
    if feature.kind == "bool":
        if bool(before) == bool(after):
            return "same"
        return "true" if bool(after) else "false"
    if int(after) > int(before):
        return "up"
    if int(after) < int(before):
        return "down"
    return "same"


def _matches(rule: dict, transition, features_by_name: dict) -> bool:
    for name, expected in rule["condition"]:
        if _valuation(features_by_name[name], transition.source) != expected:
            return False
    effects = dict(rule["effects"])
    for name, feature in features_by_name.items():
        expected = effects.get(name, "same")
        if expected == "any":
            continue
        if _effect(features_by_name[name], transition) != expected:
            return False
    return True


def _execute(policy: dict, instance, max_steps: int = 1000) -> dict:
    all_features = {f.name: f for f in feature_pool(120)}
    selected = {name: all_features[name] for name in policy["selected_features"]}
    state = instance.initial()
    seen = set()
    actions = []
    branch_counts = []
    for _ in range(max_steps):
        if state.is_goal():
            return {"solved": True, "actions": actions, "reason": "goal", "branch_counts": branch_counts}
        if state.key() in seen:
            return {"solved": False, "actions": actions, "reason": "cycle", "branch_counts": branch_counts}
        seen.add(state.key())
        candidates = [
            t for t in successors(state) if any(_matches(rule, t, selected) for rule in policy["rules"])
        ]
        branch_counts.append(len(candidates))
        if not candidates:
            return {"solved": False, "actions": actions, "reason": "undefined", "branch_counts": branch_counts}
        chosen = candidates[0]
        actions.append(chosen.action)
        state = chosen.target
    return {"solved": False, "actions": actions, "reason": "max_steps", "branch_counts": branch_counts}


def _coverage(results: list[dict]) -> float:
    return sum(result["solved"] for result in results) / len(results)


def _hard_instances(instances):
    threshold = sorted(instance.balls for instance in instances)[len(instances) // 2]
    return [instance for instance in instances if instance.balls >= threshold]


def _capacity_shift_instances():
    return [
        Instance("capacity_3_balls_8", 8, capacity=3),
        Instance("capacity_3_balls_9", 9, capacity=3),
        Instance("capacity_3_balls_14", 14, capacity=3),
        Instance("capacity_3_balls_15", 15, capacity=3),
        Instance("capacity_4_balls_20", 20, capacity=4),
        Instance("capacity_4_balls_21", 21, capacity=4),
    ]


def _branching_metrics(results: list[dict]) -> tuple[float, float]:
    counts = [count for result in results for count in result["branch_counts"]]
    if not counts:
        return 0.0, 0.0
    return float(max(counts)), sum(counts) / len(counts)


def evaluate_policy(policy: dict) -> dict[str, float]:
    train = training_instances()
    test = test_instances()
    hard = _hard_instances(test)
    capacity_shift = _capacity_shift_instances()
    train_results = [_execute(policy, inst) for inst in train]
    test_results = [_execute(policy, inst) for inst in test]
    hard_results = [_execute(policy, inst) for inst in hard]
    capacity_results = [_execute(policy, inst) for inst in capacity_shift]
    train_coverage = _coverage(train_results)
    test_coverage = _coverage(test_results)
    hard_coverage = _coverage(hard_results)
    capacity_coverage = _coverage(capacity_results)
    max_plan_ratio = 0.0
    plan_ratios = []
    for inst, result in zip(test, test_results):
        if result["solved"]:
            ratio = len(result["actions"]) / max(1, len(planner(inst)))
            plan_ratios.append(ratio)
            max_plan_ratio = max(max_plan_ratio, ratio)
    max_branching, avg_branching = _branching_metrics(test_results + capacity_results)
    policy_quality = test_coverage - 0.05 * avg_branching
    return {
        "policy_quality": policy_quality,
        "train_coverage": train_coverage,
        "large_instance_coverage": test_coverage,
        "hard_instance_coverage": hard_coverage,
        "capacity_shift_coverage": capacity_coverage,
        "max_effective_width": 0.0 if test_coverage == 1.0 else 1.0,
        "avg_effective_width": 0.0 if test_coverage == 1.0 else 1.0 - test_coverage,
        "max_applicable_successors": max_branching,
        "avg_applicable_successors": avg_branching,
        "selected_features": float(len(policy["selected_features"])),
        "policy_rules": float(len(policy["rules"])),
        "max_plan_length_ratio": max_plan_ratio,
        "avg_plan_length_ratio": sum(plan_ratios) / len(plan_ratios) if plan_ratios else 0.0,
    }


def baseline_metrics() -> dict[str, float]:
    solved = 0
    tests = test_instances()
    for inst in tests:
        state = inst.initial()
        if state.balls_at_a > 0 and state.carried < state.capacity:
            state = next(t.target for t in successors(state) if t.action == "pick")
        if state.is_goal():
            solved += 1
    return {
        "policy_quality": -0.05,
        "train_coverage": 0.0,
        "large_instance_coverage": solved / len(tests),
        "hard_instance_coverage": 0.0,
        "capacity_shift_coverage": 0.0,
        "max_effective_width": 1.0,
        "avg_effective_width": 1.0,
        "max_applicable_successors": 1.0,
        "avg_applicable_successors": 1.0,
        "selected_features": 0.0,
        "policy_rules": 1.0,
        "max_plan_length_ratio": 0.0,
        "avg_plan_length_ratio": 0.0,
        "feature_pool": 0.0,
        "inner_iterations": 0.0,
        "outer_iterations": 0.0,
        "hit_constraints": 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default="outputs/genex_gripper/policy.json")
    parser.add_argument("--include-baseline", action="store_true")
    parser.add_argument("--output", default="scoring/scores.json")
    args = parser.parse_args()

    scores = {"experiments": {"gripper_generalization": {"results": {}}}}
    if args.include_baseline:
        scores["experiments"]["gripper_generalization"]["results"]["one_step_imitation"] = baseline_metrics()

    policy_path = Path(args.policy)
    if policy_path.exists():
        policy = json.loads(policy_path.read_text())
        metrics = evaluate_policy(policy)
        stats = policy.get("stats", {})
        metrics.update(
            {
                "feature_pool": float(stats.get("feature_pool", 0)),
                "inner_iterations": float(stats.get("inner_iterations", 0)),
                "outer_iterations": float(stats.get("outer_iterations", 0)),
                "hit_constraints": float(stats.get("hit_constraints", 0)),
            }
        )
        scores["experiments"]["gripper_generalization"]["results"]["genex_wrapper"] = metrics

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")
    print(json.dumps(scores, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
