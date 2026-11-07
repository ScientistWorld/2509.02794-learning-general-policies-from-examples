"""Plan-projection baseline.

Projects every transition of the five-ball example plan onto the seven named
non-distractor features, keeping full conditions: one rule per distinct
(condition, effect) pair, without feature selection or rule simplification.
The evaluator holds a fixed copy of this policy and scores it on every slice;
this script regenerates it for inspection.
"""
from __future__ import annotations

from pathlib import Path
import json

from data.gripper import Instance, effect, feature_pool, planner, valuation

FEATURES = ["at_a", "goal", "m_carried", "n_balls_at_a", "remaining_work", "room_b", "space_in_gripper"]


def build_policy() -> dict:
    pool = {feature.name: feature for feature in feature_pool(120)}
    rules: list[dict] = []
    for transition in planner(Instance("example", 5)):
        rule = {
            "condition": [[name, valuation(pool[name], transition.source)] for name in FEATURES],
            "effects": [
                [name, effect(pool[name], transition)]
                for name in FEATURES
                if effect(pool[name], transition) != "same"
            ],
        }
        if rule not in rules:
            rules.append(rule)
    return {"selected_features": FEATURES, "rules": rules}


def main() -> None:
    out = Path("tmp/baselines/plan_projection/policy.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_policy(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
