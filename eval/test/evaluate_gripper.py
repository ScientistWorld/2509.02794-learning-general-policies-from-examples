from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from data.gripper import feature_pool, planner, successors, test_instances, training_instances


SLICE = "test"
OUTPUT = "scoring/scores_test.json"
TRAIN_SCORES = "scoring/scores_train.json"
EXPERIMENT = "gripper_generalization"


def _slice_instances():
    return [instance for index, instance in enumerate(test_instances()) if index % 2 == 1]


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
        if _effect(feature, transition) != expected:
            return False
    return True


def _execute(policy: dict, instance, max_steps: int = 1000) -> dict:
    all_features = {feature.name: feature for feature in feature_pool(120)}
    selected = {name: all_features[name] for name in policy["selected_features"]}
    state = instance.initial()
    seen = set()
    actions = []
    for _ in range(max_steps):
        if state.is_goal():
            return {"solved": True, "actions": actions, "reason": "goal"}
        if state.key() in seen:
            return {"solved": False, "actions": actions, "reason": "cycle"}
        seen.add(state.key())
        candidates = [
            transition
            for transition in successors(state)
            if any(_matches(rule, transition, selected) for rule in policy["rules"])
        ]
        if not candidates:
            return {"solved": False, "actions": actions, "reason": "undefined"}
        chosen = candidates[0]
        actions.append(chosen.action)
        state = chosen.target
    return {"solved": False, "actions": actions, "reason": "max_steps"}


def evaluate_policy(policy: dict) -> dict[str, float]:
    train = training_instances()
    large = _slice_instances()
    train_results = [_execute(policy, instance) for instance in train]
    large_results = [_execute(policy, instance) for instance in large]
    train_coverage = sum(result["solved"] for result in train_results) / len(train_results)
    large_coverage = sum(result["solved"] for result in large_results) / len(large)
    max_plan_ratio = 0.0
    for instance, result in zip(large, large_results):
        if result["solved"]:
            max_plan_ratio = max(max_plan_ratio, len(result["actions"]) / max(1, len(planner(instance))))
    return {
        "train_coverage": train_coverage,
        "large_instance_coverage": large_coverage,
        "max_effective_width": 0.0 if large_coverage == 1.0 else 1.0,
        "avg_effective_width": 0.0 if large_coverage == 1.0 else 1.0 - large_coverage,
        "selected_features": float(len(policy["selected_features"])),
        "policy_rules": float(len(policy["rules"])),
        "max_plan_length_ratio": max_plan_ratio,
    }


def baseline_metrics() -> dict[str, float]:
    solved = 0
    large = _slice_instances()
    for instance in large:
        state = instance.initial()
        if state.balls_at_a > 0 and state.carried < state.capacity:
            state = next(transition.target for transition in successors(state) if transition.action == "pick")
        if state.is_goal():
            solved += 1
    return {
        "train_coverage": 0.0,
        "large_instance_coverage": solved / len(large),
        "max_effective_width": 1.0,
        "avg_effective_width": 1.0,
        "selected_features": 0.0,
        "policy_rules": 1.0,
        "max_plan_length_ratio": 0.0,
    }


def _discover_policy_paths() -> list[Path]:
    roots = [Path("outputs"), Path("checkpoints"), Path("method_outputs")]
    paths: list[Path] = []
    for root in roots:
        if root.exists():
            paths.extend(root.glob("**/policy.json"))
    return sorted(set(paths))


def _method_name(path: Path) -> str:
    parent = path.parent.name if path.parent.name else path.stem
    name = re.sub(r"[^A-Za-z0-9_.-]+", "_", parent).strip("_")
    return name or "policy"


def _named_policy_paths(paths: list[Path]) -> dict[str, Path]:
    named: dict[str, Path] = {}
    for path in paths:
        base = _method_name(path)
        name = base
        suffix = 2
        while name in named:
            name = f"{base}_{suffix}"
            suffix += 1
        named[name] = path
    return named


def _train_method_names(path: Path) -> list[str] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    results = payload.get("experiments", {}).get(EXPERIMENT, {}).get("results", {})
    return list(results)


def _metrics_for_policy(path: Path) -> dict[str, float]:
    policy = json.loads(path.read_text())
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
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=None, help="Optional single policy.json artifact to score.")
    parser.add_argument("--include-baseline", action="store_true")
    parser.add_argument("--output", default=OUTPUT)
    parser.add_argument("--train-scores", default=TRAIN_SCORES)
    args = parser.parse_args()

    paths = [Path(args.policy)] if args.policy else _discover_policy_paths()
    named_paths = _named_policy_paths([path for path in paths if path.exists()])
    train_names = _train_method_names(Path(args.train_scores))
    requested = train_names if train_names is not None else list(named_paths)

    missing = sorted(name for name in requested if name != "one_step_imitation" and name not in named_paths)
    if missing:
        raise SystemExit(
            "Could not find policy artifacts for method(s) listed in train scores: " + ", ".join(missing)
        )

    scores = {"experiments": {EXPERIMENT: {"results": {}}}}
    results = scores["experiments"][EXPERIMENT]["results"]
    if args.include_baseline or "one_step_imitation" in requested:
        results["one_step_imitation"] = baseline_metrics()

    for method_name in requested:
        if method_name == "one_step_imitation":
            continue
        results[method_name] = _metrics_for_policy(named_paths[method_name])

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")
    print(json.dumps(scores, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
