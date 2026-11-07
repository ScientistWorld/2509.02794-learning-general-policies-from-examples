"""Run the paper's method (GENEX + WRAPPER) on both benchmark domains.

Writes the method's policy artifacts:
  outputs/genex_wrapper/policy.json             (Gripper)
  outputs/genex_wrapper/childsnack_policy.json  (Childsnack)
"""
from __future__ import annotations

import sys
from pathlib import Path

from data import childsnack, gripper
from method.genex import learn_policy, policy_to_json

ARTIFACTS = {
    "gripper": (gripper, "policy.json"),
    "childsnack": (childsnack, "childsnack_policy.json"),
}


def main() -> None:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("outputs/genex_wrapper")
    for name, (domain, filename) in ARTIFACTS.items():
        policy, stats = learn_policy(domain)
        out = out_dir / filename
        policy_to_json(policy, stats, out)
        print(f"[{name}] wrote {out}: {stats}")


if __name__ == "__main__":
    main()
