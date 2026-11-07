#!/bin/bash
# Default evaluation: scores every policy artifact on disk on the visible slice.
#
# Self-contained in eval/: does not import method/ or data/. A policy artifact is
# any outputs/**/policy.json, checkpoints/**/policy.json or
# method_outputs/**/policy.json; the method name is the artifact's directory
# name. Writes scoring/scores.json (also includes the evaluator-owned baselines).
#
# Usage:
#   bash scripts/evaluate.sh                         # every artifact on disk
#   bash scripts/evaluate.sh --policy path/to/policy.json

set -e

cd /home/user

mkdir -p scoring

python -m eval.evaluate_gripper "$@"
