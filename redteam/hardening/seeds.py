"""Relearn the reference policy under three hash seeds and score each on the hidden test.

    python -m redteam.hardening.seeds

Writes redteam/hardening/seeds.json. Uses tmp/ only; does not touch outputs/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/user")
os.chdir(ROOT)
LEARN = (
    "from pathlib import Path; import sys\n"
    "from method.genex import learn_gripper_policy, policy_to_json\n"
    "policy, stats = learn_gripper_policy()\n"
    "policy_to_json(policy, stats, Path(sys.argv[1]))\n"
)


def main() -> None:
    record = {}
    for seed in (0, 1, 2):
        work = ROOT / "tmp" / "seeds" / f"seed_{seed}"
        work.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, PYTHONHASHSEED=str(seed))
        artifact = work / "policy.json"
        subprocess.run([sys.executable, "-c", LEARN, str(artifact)], env=env, check=True)
        out = work / "scores_test.json"
        subprocess.run([sys.executable, "-m", "eval.test.evaluate_gripper", "--no-baselines", "--policy",
                        str(artifact), "--output", str(out)], env=env, check=True, stdout=subprocess.DEVNULL)
        scores = json.loads(out.read_text())["experiments"]["gripper_generalization"]["results"]
        policy = json.loads(artifact.read_text())
        record[str(seed)] = {"rules": policy["rules"], "selected_features": policy["selected_features"],
                             "test_metrics": next(iter(scores.values()))}
    identical = all(record[s] == record["0"] for s in record)
    reference = json.loads(Path("scoring/reference.json").read_text())
    coefficients = {m: d["coefficient"] for m, d in
                    reference["experiments"]["gripper_generalization"]["metrics"].items()}
    weighted = {s: sum(c * r["test_metrics"].get(m, 0.0) for m, c in coefficients.items()) for s, r in record.items()}
    summary = {"identical_policies_and_scores": identical, "weighted_test_score": weighted,
               "spread": max(weighted.values()) - min(weighted.values()), "seeds": record}
    (ROOT / "redteam" / "hardening" / "seeds.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: summary[k] for k in ("identical_policies_and_scores", "weighted_test_score", "spread")}))


if __name__ == "__main__":
    main()
