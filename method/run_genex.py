from __future__ import annotations

from pathlib import Path

from method.genex import learn_gripper_policy, policy_to_json


def main() -> None:
    policy, stats = learn_gripper_policy()
    out = Path("outputs/genex_gripper/policy.json")
    policy_to_json(policy, stats, out)
    print(f"wrote {out}")
    print(stats)


if __name__ == "__main__":
    main()
