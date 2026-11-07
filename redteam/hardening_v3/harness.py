"""Hardening audit (iteration 12): every case through the hidden test, alone.

For each case:
  1. its learner (or fixed artifact) writes a method directory under
     redteam/hardening_v3/cases/<case>/artifacts/;
  2. `outputs/` is moved aside and replaced by `outputs/<case>/` holding only
     that case's artifacts;
  3. `bash scripts/evaluate_test.sh` runs with no arguments, in a fresh process;
  4. the scores are saved and the real `outputs/` and score file restored.

The reference is relearned three times with PYTHONHASHSEED 0, 1, 2. Ranks use
`scoring/reference.json`: sum over experiments of weight x sum over metrics of
coefficient x (case - reference), against the seed-0 reference's test scores.

Usage: python -m redteam.hardening_v3.harness [case ...]
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES_DIR = HERE / "cases"
SCORES_TEST = ROOT / "scoring" / "scores_test.json"


BUILD_TIMEOUT_S = 2400  # a learner that exceeds this is recorded as failed (no artifact)
BUILD_STATUS: dict[str, object] = {}


def _run(cmd: list[str], env: dict | None = None, log: Path | None = None, timeout: float | None = None) -> int:
    start = time.time()
    with open(log, "w") if log else open(os.devnull, "w") as handle:
        try:
            rc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            handle.write(f"\n[harness] timed out after {timeout}s\n")
            rc = "timeout"
    print(f"  {' '.join(cmd)} -> rc={rc} ({time.time() - start:.1f}s)", flush=True)
    return rc


def build(case: str, ref_dir: Path | None, seed: int = 0) -> Path:
    out = CASES_DIR / case / "artifacts"
    if out.exists():
        shutil.rmtree(out)
    env = dict(os.environ, PYTHONHASHSEED=str(seed), PYTHONPATH=str(ROOT))
    args = [sys.executable, "-m", "redteam.hardening_v3.variants", case.split("@")[0], str(out)]
    if ref_dir is not None:
        args.append(str(ref_dir))
    (CASES_DIR / case).mkdir(parents=True, exist_ok=True)
    rc = _run(args, env=env, log=CASES_DIR / case / "method.log", timeout=BUILD_TIMEOUT_S)
    if rc != 0:
        out.mkdir(parents=True, exist_ok=True)
    BUILD_STATUS[case] = rc
    return out


def score_alone(case: str, artifacts: Path) -> dict:
    outputs = ROOT / "outputs"
    parked = ROOT / "tmp" / "hardening_v3_parked_outputs"
    saved_scores = SCORES_TEST.read_bytes() if SCORES_TEST.exists() else None
    if parked.exists():
        shutil.rmtree(parked)
    parked.parent.mkdir(parents=True, exist_ok=True)
    if outputs.exists():
        shutil.move(str(outputs), str(parked))
    try:
        staged = outputs / case.replace("@", "_seed")
        staged.mkdir(parents=True)
        for item in artifacts.iterdir():
            shutil.copy(item, staged / item.name)
        _run(["bash", "scripts/evaluate_test.sh"], log=CASES_DIR / case / "test.log")
        scores = json.loads(SCORES_TEST.read_text())
        (CASES_DIR / case / "scores_test.json").write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")
        return scores
    finally:
        if outputs.exists():
            shutil.rmtree(outputs)
        if parked.exists():
            shutil.move(str(parked), str(outputs))
        if saved_scores is not None:
            SCORES_TEST.write_bytes(saved_scores)


def method_metrics(scores: dict, case: str) -> dict:
    name = case.replace("@", "_seed")
    return {exp: data["results"][name] for exp, data in scores["experiments"].items() if name in data["results"]}


def weighted(metrics: dict, reference: dict) -> dict:
    out = {"total": 0.0}
    for exp, spec in reference["experiments"].items():
        value = sum(m["coefficient"] * metrics.get(exp, {}).get(name, 0.0) for name, m in spec["metrics"].items())
        out[exp] = value
        out["total"] += spec["weight"] * value
    return out


def main() -> None:
    reference_spec = json.loads((ROOT / "scoring" / "reference.json").read_text())
    from redteam.hardening_v3.variants import CASES

    wanted = sys.argv[1:] or list(CASES)
    results: dict = {}
    seeds = {}
    for seed in (0, 1, 2):
        case = f"reference@{seed}"
        print(f"[case] {case}", flush=True)
        artifacts = build(case, None, seed)
        seeds[seed] = {f.name: f.read_text() for f in sorted(artifacts.iterdir())}
        metrics = method_metrics(score_alone(case, artifacts), case)
        results[case] = {"metrics": metrics, "weighted": weighted(metrics, reference_spec)}
    ref_dir = CASES_DIR / "reference@0" / "artifacts"
    ref_weighted = results["reference@0"]["weighted"]
    for case in wanted:
        if case == "reference":
            continue
        print(f"[case] {case}", flush=True)
        artifacts = build(case, ref_dir)
        metrics = method_metrics(score_alone(case, artifacts), case)
        results[case] = {"metrics": metrics, "weighted": weighted(metrics, reference_spec)}
    for case, record in results.items():
        record["rank_vs_reference"] = {
            key: (record["weighted"][key] - ref_weighted[key]) * (
                reference_spec["experiments"][key]["weight"] if key in reference_spec["experiments"] else 1.0)
            for key in record["weighted"]
        }
    summary = {
        "reference_seeds_identical": seeds[0] == seeds[1] == seeds[2],
        "reference_weighted_by_seed": {s: results[f"reference@{s}"]["weighted"]["total"] for s in (0, 1, 2)},
        "cases": results,
        "build_returncodes": BUILD_STATUS,
    }
    (HERE / "results.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(f"{'case':42s} {'gripper':>10s} {'childsnack':>11s} {'rank':>10s}")
    for case, record in results.items():
        r = record["rank_vs_reference"]
        print(f"{case:42s} {r['gripper_generalization']:10.4f} {r['childsnack_generalization']:11.4f} {r['total']:10.4f}")
    print("reference seeds identical:", summary["reference_seeds_identical"])


if __name__ == "__main__":
    main()
