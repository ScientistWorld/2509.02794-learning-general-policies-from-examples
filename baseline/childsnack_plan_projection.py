"""Childsnack plan-projection baseline.

Projects every transition of the example plan of the first learning instance in
WRAPPER's order (p-3-1.0-0.67-1-2) onto all named non-distractor features,
keeping full conditions: one rule per distinct (condition, effect) pair, with no
feature selection or rule simplification. The evaluator holds a fixed copy of
this policy; this script regenerates it for inspection.
"""
from __future__ import annotations

from pathlib import Path
import json

from data.childsnack import effect, feature_pool, planner, training_instances, valuation

EXAMPLE = "p-3-1.0-0.67-1-2"


def build_policy() -> dict:
    pool = [f for f in feature_pool(0)]
    names = sorted(f.name for f in pool)
    by_name = {f.name: f for f in pool}
    instance = next(inst for inst in training_instances() if inst.name == EXAMPLE)
    rules: list[dict] = []
    for transition in planner(instance):
        rule = {
            "condition": [[name, valuation(by_name[name], transition.source)] for name in names],
            "effects": [
                [name, effect(by_name[name], transition)]
                for name in names
                if effect(by_name[name], transition) != "same"
            ],
        }
        if rule not in rules:
            rules.append(rule)
    return {"selected_features": names, "rules": rules}


def main() -> None:
    out = Path("tmp/baselines/childsnack_plan_projection/childsnack_policy.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_policy(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
