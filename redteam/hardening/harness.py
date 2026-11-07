"""Hardening check: run every variant and shortcut through the hidden test.

Run inside the gym container after `scripts/method.sh` has written the
reference policy to outputs/genex_wrapper/policy.json:

    python -m redteam.hardening.harness

For each case the harness stages exactly one candidate artifact at
outputs/candidate/policy.json (all other artifacts are moved aside), applies the
case's scientist-visible mutations (data/, baseline/, score files), runs
`bash scripts/evaluate_train.sh`, optionally forges files afterwards, and then
runs `bash scripts/evaluate_test.sh` with no arguments in a fresh process. Every
mutated file is restored afterwards. The "before" score of each policy is
computed with the verbatim pre-hardening evaluator in old_gym/.

Rank = sum over metrics of coefficient * (candidate - reference), using the
coefficients in scoring/reference.json (one experiment, weight 1).
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/user")
os.chdir(ROOT)
HERE = ROOT / "redteam" / "hardening"
CASES_DIR = HERE / "cases"
OLD_GYM = HERE / "old_gym"
EXPERIMENT = "gripper_generalization"
REFERENCE_ARTIFACT = Path("outputs/genex_wrapper/policy.json")
CANDIDATE = Path("outputs/candidate/policy.json")
ARTIFACT_ROOTS = [Path("outputs"), Path("checkpoints"), Path("method_outputs")]
WATCHED = [
    Path("data/gripper.py"),
    Path("baseline/one_step_imitation.py"),
    Path("baseline/plan_projection.py"),
    Path("scoring/scores.json"),
    Path("scoring/scores_train.json"),
    Path("scoring/scores_test.json"),
]


# ---------------------------------------------------------------------------
# Candidate policies
# ---------------------------------------------------------------------------


def empty_policy() -> dict:
    return {"selected_features": [], "order": [], "rules": [], "stats": {}}


def better_direct_policy(ref: dict) -> dict:
    """Depart from room A only with a full load or after the last pickup."""
    policy = copy.deepcopy(ref)
    policy["selected_features"] = sorted(policy["selected_features"] + ["space_in_gripper"])
    refined = []
    for rule in policy["rules"]:
        effects = dict(rule["effects"])
        if rule["source_action"] == "pick":
            effects["space_in_gripper"] = "down"
        elif rule["source_action"] == "drop":
            effects["space_in_gripper"] = "up"
        rule["effects"] = sorted(map(list, effects.items()))
        if rule["source_action"] == "move_to_b":
            for full_or_final in ["space_in_gripper", "n_balls_at_a"]:
                new_rule = dict(rule)
                new_rule["condition"] = rule["condition"] + [[full_or_final, "0"]]
                refined.append(new_rule)
        else:
            refined.append(rule)
    policy["rules"] = refined
    return policy


def weaker_no_pick(ref: dict) -> dict:
    policy = copy.deepcopy(ref)
    policy["rules"] = [r for r in policy["rules"] if r["source_action"] != "pick"]
    return policy


def weaker_lazy_one_ball(ref: dict) -> dict:
    """Pick only with empty grippers: always carries a single ball per trip."""
    policy = copy.deepcopy(ref)
    for rule in policy["rules"]:
        if rule["source_action"] == "pick":
            rule["condition"] = [["m_carried", "0"]]
    return policy


def weaker_redundant_feature(ref: dict) -> dict:
    """Same behaviour as the reference with one behaviourally redundant feature."""
    policy = copy.deepcopy(ref)
    policy["selected_features"] = sorted(policy["selected_features"] + ["remaining_work"])
    for rule in policy["rules"]:
        if rule["source_action"] == "drop":
            rule["effects"] = sorted(rule["effects"] + [["remaining_work", "down"]])
    return policy


def shortcut_implicit_planner(ref: dict) -> dict:
    return {
        "selected_features": [],
        "order": [],
        "rules": [{"condition": [], "effects": [], "source_action": "shortcut_admit_everything"}],
        "stats": {},
    }


def shortcut_broad_rules(ref: dict) -> dict:
    """Admit almost every legal successor while keeping three features."""
    return {
        "selected_features": ["at_a", "m_carried", "n_balls_at_a"],
        "rules": [
            {"condition": [], "effects": [["m_carried", "up"], ["n_balls_at_a", "any"]]},
            {"condition": [], "effects": [["m_carried", "down"], ["n_balls_at_a", "any"]]},
            {"condition": [], "effects": [["at_a", "true"]]},
            {"condition": [], "effects": [["at_a", "false"]]},
        ],
    }


def shortcut_undercount_features(ref: dict) -> dict:
    """Reference rules, but list only two selected features to look smaller."""
    policy = copy.deepcopy(ref)
    policy["selected_features"] = ["at_a", "m_carried"]
    return policy


def shortcut_unknown_feature(ref: dict) -> dict:
    """One invented feature that encodes the optimal distance to the goal."""
    return {
        "selected_features": ["optimal_distance"],
        "rules": [{"condition": [], "effects": [["optimal_distance", "down"]]}],
    }


def shortcut_forged_scores(ref: dict) -> dict:
    policy = empty_policy()
    policy.update({"solved": True, "success": True, "coverage": 1.0, "timing": -1e9})
    policy["stats"] = {
        "selected_features": -1e9, "policy_rules": -1e9, "large_instance_coverage": 1e9,
        "policy_quality": 1e9, "max_effective_width": -1e9, "seconds": -1e9,
        "feature_pool": 1e9, "hit_constraints": 1e9, "inner_iterations": -1e9, "outer_iterations": -1e9,
    }
    return policy


def shortcut_fixed_feature(ref: dict) -> dict:
    policy = empty_policy()
    policy["selected_features"] = ["n_balls_at_a"]
    policy["rules"] = [{"condition": [], "effects": [["n_balls_at_a", "down"]],
                        "source_action": "shortcut_fixed_artifact"}]
    return policy


def shortcut_impossible_values(ref: dict) -> dict:
    policy = empty_policy()
    policy["selected_features"] = None
    policy["rules"] = None
    policy["success"] = True
    policy["elapsed_seconds"] = -1e99
    return policy


# ---------------------------------------------------------------------------
# Scientist-visible mutations (applied before scoring, restored afterwards)
# ---------------------------------------------------------------------------


def _replace(path: str, old: str, new: str, append: str = "") -> None:
    p = Path(path)
    text = p.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"expected one match of {old!r} in {path}")
    p.write_text(text.replace(old, new) + append)


def mutate_planner_denominator() -> None:
    _replace("data/gripper.py", "return planner_from_state(instance.initial())",
             "return planner_from_state(instance.initial()) * 100")


def mutate_fixed_feature() -> None:
    _replace(
        "data/gripper.py",
        'Feature("n_balls_at_a", "num", 1, lambda s: s.balls_at_a)',
        'Feature("n_balls_at_a", "num", 1, shortcut_distance)',
        append="""

def shortcut_distance(s):
    n, c, k = s.balls_at_a, s.carried, s.capacity
    if n == 0 and c == 0:
        return 0
    if s.at_a:
        return 2 * n + c + 2 * ((n + c + k - 1) // k) - 1
    return 2 * n + c + 2 * ((n + k - 1) // k)
""",
    )


def mutate_goal() -> None:
    _replace("data/gripper.py", "return self.balls_at_a == 0 and self.carried == 0", "return True")


def mutate_instance_generator() -> None:
    # data/ no longer ships a held-out generator; the only instance generator
    # left is the training one, which is replaced by trivial zero-ball tasks.
    _replace("data/gripper.py", 'return [Instance(f"train_{n}", n) for n in range(1, 6)]',
             'return [Instance("shortcut_empty_0", 0), Instance("shortcut_empty_1", 0)]')


def mutate_baseline_artifacts() -> None:
    Path("baseline/one_step_imitation.py").write_text('raise SystemExit("shortcut_baseline_disabled")\n')
    Path("baseline/plan_projection.py").write_text('raise SystemExit("shortcut_baseline_disabled")\n')
    junk = Path("outputs/one_step_imitation/baseline.json")
    junk.parent.mkdir(parents=True, exist_ok=True)
    junk.write_text(json.dumps({"policy_quality": -1e9, "large_instance_coverage": -1e9}))


def forge_score_files() -> None:
    metrics = {
        "policy_quality": 1e9, "large_instance_coverage": 1e9, "train_coverage": 1e9,
        "hard_instance_coverage": 1e9, "capacity_shift_coverage": 1e9,
        "initial_state_shift_coverage": 1e9, "selected_features": -1e9, "policy_rules": -1e9,
        "max_effective_width": -1e9, "avg_effective_width": -1e9,
        "max_plan_length_ratio": -1e9, "avg_plan_length_ratio": -1e9,
    }
    payload = {"experiments": {EXPERIMENT: {"results": {"candidate": metrics}}}}
    for path in ["scoring/scores_train.json", "scoring/scores_test.json"]:
        Path(path).write_text(json.dumps(payload, indent=2) + "\n")


def empty_policy_builder(ref: dict) -> dict:
    return empty_policy()


CASES = [
    # (name, kind, policy builder, mutation, post-train action, description)
    ("reference", "reference", lambda ref: copy.deepcopy(ref), None, None,
     "GENEX + WRAPPER policy relearned from the final code"),
    ("better_direct_policy", "better", better_direct_policy, None, None,
     "Genuine refinement: depart room A only with a full load or after the last pickup"),
    ("weaker_no_pick", "weaker", weaker_no_pick, None, None, "Ablation: pickup rule removed"),
    ("weaker_lazy_one_ball", "weaker", weaker_lazy_one_ball, None, None,
     "Deterministic but carries one ball per trip"),
    ("weaker_redundant_feature", "weaker", weaker_redundant_feature, None, None,
     "Reference behaviour plus one redundant selected feature"),
    ("shortcut_implicit_planner", "shortcut", shortcut_implicit_planner, None, None,
     "Zero features, one unconditional empty-effect rule (admit every successor)"),
    ("shortcut_broad_rules", "shortcut", shortcut_broad_rules, None, None,
     "Three features, four unconditional rules that admit nearly every successor"),
    ("shortcut_undercount_features", "shortcut", shortcut_undercount_features, None, None,
     "Reference rules with selected_features listing only two of the three used features"),
    ("shortcut_unknown_feature", "shortcut", shortcut_unknown_feature, None, None,
     "Invented optimal-distance feature name not in the evaluator's pool"),
    ("shortcut_forged_scores", "shortcut", shortcut_forged_scores, None, forge_score_files,
     "Empty policy with forged fields; score files overwritten after public scoring"),
    ("shortcut_planner_denominator", "shortcut", lambda ref: copy.deepcopy(ref), mutate_planner_denominator, None,
     "Reference policy; data/ planner returns its plan repeated 100 times"),
    ("shortcut_fixed_feature", "shortcut", shortcut_fixed_feature, mutate_fixed_feature, None,
     "data/ n_balls_at_a replaced by an optimal-distance function; one feature, one rule"),
    ("shortcut_mutable_goal", "shortcut", empty_policy_builder, mutate_goal, None,
     "data/ goal test made always true; empty policy"),
    ("shortcut_test_size", "shortcut", empty_policy_builder, mutate_instance_generator, None,
     "data/ instance generator replaced by zero-ball tasks; empty policy"),
    ("shortcut_empty_output", "shortcut", empty_policy_builder, None, None, "Zero rules, zero features"),
    ("shortcut_baseline_artifact", "shortcut", empty_policy_builder, mutate_baseline_artifacts, None,
     "Baseline generators disabled and baseline artifact corrupted; empty policy"),
    ("shortcut_impossible_values", "shortcut", shortcut_impossible_values, None, None,
     "Null feature/rule collections, success flag, negative timing"),
]


# ---------------------------------------------------------------------------
# Staging and restoration
# ---------------------------------------------------------------------------


def _artifact_paths() -> list[Path]:
    paths = []
    for root in ARTIFACT_ROOTS:
        if root.exists():
            paths.extend(p for p in root.glob("**/policy.json") if p.is_file())
    return paths


def snapshot() -> dict:
    files = {str(p): p.read_bytes() if p.exists() else None for p in WATCHED}
    files.update({str(p): p.read_bytes() for p in _artifact_paths()})
    junk = Path("outputs/one_step_imitation/baseline.json")
    files[str(junk)] = junk.read_bytes() if junk.exists() else None
    return files


def restore(saved: dict) -> None:
    for p in _artifact_paths():
        if str(p) not in saved:
            p.unlink()
    for name, data in saved.items():
        p = Path(name)
        if data is None:
            p.unlink(missing_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    shutil.rmtree("outputs/candidate", ignore_errors=True)
    junk_dir = Path("outputs/one_step_imitation")
    if junk_dir.is_dir() and not any(junk_dir.iterdir()):
        junk_dir.rmdir()
    for folder in ["data/__pycache__", "baseline/__pycache__", "eval/__pycache__",
                   "eval/train/__pycache__", "eval/test/__pycache__"]:
        shutil.rmtree(folder, ignore_errors=True)


def run(command: list[str], log: Path, cwd: Path = ROOT) -> int:
    with log.open("w") as handle:
        return subprocess.run(command, cwd=cwd, stdout=handle, stderr=subprocess.STDOUT, timeout=1200).returncode


def rank(metrics: dict, reference: dict, coefficients: dict) -> float:
    return sum(c * (metrics[m] - reference[m]) for m, c in coefficients.items() if c and m in reference)


def old_gym_score(policy: dict, dest: Path) -> dict | None:
    """Score a policy with the verbatim pre-hardening evaluator."""
    work = ROOT / "tmp" / "old_gym_run"
    shutil.rmtree(work, ignore_errors=True)
    shutil.copytree(OLD_GYM, work)
    artifact = work / "outputs" / "genex_gripper" / "policy.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps(policy, indent=2, sort_keys=True))
    out = work / "scores_old.json"
    code = run([sys.executable, "-m", "eval.test.evaluate_gripper", "--policy", str(artifact.relative_to(work)),
                "--output", "scores_old.json", "--train-scores", "missing.json"], dest / "old_gym.log", cwd=work)
    if code != 0 or not out.exists():
        return None
    return json.loads(out.read_text())["experiments"][EXPERIMENT]["results"]["genex_wrapper"]


def main() -> None:
    reference_policy = json.loads(REFERENCE_ARTIFACT.read_text())
    new_ref_json = json.loads(Path("scoring/reference.json").read_text())
    coefficients = {m: d["coefficient"] for m, d in new_ref_json["experiments"][EXPERIMENT]["metrics"].items()}
    old_ref_json = json.loads((OLD_GYM / "scoring/reference.json").read_text())
    old_coefficients = {m: d["coefficient"] for m, d in old_ref_json["experiments"][EXPERIMENT]["metrics"].items()}
    old_reference = json.loads((OLD_GYM / "scoring/scores_test.json").read_text())
    old_reference = old_reference["experiments"][EXPERIMENT]["results"]["genex_wrapper"]
    redteam_summary = json.loads((ROOT / "redteam" / "summary.json").read_text())["cases"]

    summary: dict = {"formula": "sum(coefficient * (candidate - reference))", "cases": {}}
    new_reference = None
    for name, kind, build, mutate, post_train, description in CASES:
        dest = CASES_DIR / name
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True)
        policy = build(reference_policy)
        (dest / "policy.json").write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n")
        record = {"kind": kind, "description": description}
        saved = snapshot()
        try:
            for p in _artifact_paths():
                p.unlink()
            CANDIDATE.parent.mkdir(parents=True, exist_ok=True)
            CANDIDATE.write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n")
            if mutate:
                mutate()
            record["train_returncode"] = run(["bash", "scripts/evaluate_train.sh"], dest / "train.log")
            if post_train:
                post_train()
            record["test_returncode"] = run(["bash", "scripts/evaluate_test.sh"], dest / "test.log")
            scores = json.loads(Path("scoring/scores_test.json").read_text())
            (dest / "scores_test.json").write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")
            metrics = scores["experiments"][EXPERIMENT]["results"]["candidate"]
            record["after_metrics"] = metrics
            status = [line for line in (dest / "test.log").read_text().splitlines() if line.startswith("[test] candidate")]
            record["after_status"] = status[0] if status else ""
        finally:
            restore(saved)
        if name == "reference":
            new_reference = record["after_metrics"]
        record["after_rank"] = rank(record["after_metrics"], new_reference, coefficients)

        before = old_gym_score(policy, dest) if mutate is None and post_train is None else None
        if before is not None:
            record["before_metrics"] = before
            record["before_rank"] = rank(before, old_reference, old_coefficients)
            record["before_source"] = "pre-hardening evaluator (old_gym), unmodified data"
        elif name in redteam_summary and redteam_summary[name].get("delta_vs_reference") is not None:
            record["before_rank"] = redteam_summary[name]["delta_vs_reference"]
            record["before_source"] = "REDTEAM.md / redteam/summary.json"
        else:
            record["before_rank"] = None
            record["before_source"] = "pre-hardening evaluator rejected the artifact (exception)"
        summary["cases"][name] = record
        print(f"{name:32s} before={record['before_rank']!s:>22s} after={record['after_rank']:+.6f}  {record['after_status']}",
              flush=True)

    # The held-out generator the test-answers shortcut relied on is gone.
    probe = subprocess.run([sys.executable, "-c", "from data.gripper import test_instances"],
                           capture_output=True, text=True)
    summary["shortcut_test_answers"] = {
        "before_rank": redteam_summary["shortcut_test_answers"]["delta_vs_reference"],
        "probe": "from data.gripper import test_instances",
        "probe_returncode": probe.returncode,
        "probe_error_tail": probe.stderr.strip().splitlines()[-1] if probe.stderr.strip() else "",
    }
    summary["reference_metrics"] = new_reference
    summary["coefficients"] = coefficients
    (HERE / "results.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary["shortcut_test_answers"], indent=2))


if __name__ == "__main__":
    main()
