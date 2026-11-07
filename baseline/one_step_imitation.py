"""One-step imitation baseline.

Imitates only the first action of the example plans: the projection of the
first planner transition (a pick in room A) onto the two features it changes,
with no conditions. The evaluator holds a fixed copy of this policy and scores
it on every slice; this script regenerates it for inspection.
"""
from __future__ import annotations

from pathlib import Path
import json

from data.gripper import Instance, effect, feature_pool, planner

FEATURES = ["m_carried", "n_balls_at_a"]


def build_policy() -> dict:
    pool = {feature.name: feature for feature in feature_pool(120)}
    first = planner(Instance("example", 5))[0]
    effects = [[name, effect(pool[name], first)] for name in FEATURES if effect(pool[name], first) != "same"]
    return {"selected_features": FEATURES, "rules": [{"condition": [], "effects": effects}]}


def main() -> None:
    out = Path("tmp/baselines/one_step_imitation/policy.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build_policy(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
