"""Hidden test-slice entry point (scripts/evaluate_test.sh).

Scores every method on disk on every experiment and writes
`scoring/scores_test.json`. A method is a directory under `outputs/`,
`checkpoints/` or `method_outputs/` that holds at least one policy artifact:

- `policy.json`            -> experiment `gripper_generalization`
- `childsnack_policy.json` -> experiment `childsnack_generalization`

The method name is the directory name. A method that lacks one of the two
artifacts is scored as failed on that experiment. Only the `selected_features`
and `rules` fields of an artifact are read; every number is recomputed here,
along with the evaluator-owned baselines.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from eval.test import evaluate_childsnack, evaluate_gripper

SLICE = "test"
OUTPUT = "scoring/scores_test.json"
ROOTS = ("outputs", "checkpoints", "method_outputs")
EXPERIMENTS = {
    evaluate_gripper.EXPERIMENT: ("policy.json", evaluate_gripper),
    evaluate_childsnack.EXPERIMENT: ("childsnack_policy.json", evaluate_childsnack),
}
BASELINE_NAMES = set(evaluate_gripper.BASELINES) | set(evaluate_childsnack.BASELINES)


def _discover_method_dirs(roots=ROOTS) -> list[Path]:
    artifacts = {artifact for artifact, _ in EXPERIMENTS.values()}
    dirs: set[Path] = set()
    for root in roots:
        root_path = Path(root)
        if not root_path.exists():
            continue
        for artifact in artifacts:
            dirs.update(p.parent for p in root_path.glob(f"**/{artifact}") if p.is_file())
    return sorted(dirs)


def _name_methods(dirs: list[Path]) -> dict[str, Path]:
    named: dict[str, Path] = {}
    for directory in dirs:
        base = re.sub(r"[^A-Za-z0-9_.-]+", "_", directory.name).strip("_") or "policy"
        if base in BASELINE_NAMES:
            base = f"{base}_submitted"
        name = base
        suffix = 2
        while name in named:
            name = f"{base}_{suffix}"
            suffix += 1
        named[name] = directory
    return named


def _load(path: Path):
    if not path.is_file():
        return {"_missing": str(path)}
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, ValueError) as error:
        return {"_unreadable": str(error)}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method-dir", action="append", default=None,
                        help="Score only these method directories instead of every one on disk.")
    parser.add_argument("--output", default=OUTPUT)
    parser.add_argument("--no-baselines", action="store_true")
    args = parser.parse_args(argv)

    dirs = [Path(d) for d in args.method_dir] if args.method_dir else _discover_method_dirs()
    methods = _name_methods(dirs)
    experiments: dict = {}
    for experiment, (artifact, module) in EXPERIMENTS.items():
        results: dict = {}
        if not args.no_baselines:
            for name, payload in module.BASELINES.items():
                metrics, status = module.evaluate_payload(payload)
                results[name] = metrics
                print(f"[{SLICE}] {experiment} {name}: {status}")
        for name, directory in methods.items():
            payload = _load(directory / artifact)
            metrics, status = module.evaluate_payload(payload)
            if isinstance(payload, dict) and "_missing" in payload:
                status = "missing artifact (scored as failed)"
            results[name] = metrics
            print(f"[{SLICE}] {experiment} {name} ({directory / artifact}): {status}")
        experiments[experiment] = {"results": results}

    scores = {"slice": SLICE, "experiments": experiments}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(scores, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
