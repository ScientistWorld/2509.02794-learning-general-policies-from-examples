#!/bin/bash
# Run the simple reference baseline used by this gym.
#
# The baseline is intentionally weak: it imitates one local action and then
# stops. Its purpose is to verify that the evaluator distinguishes a direct
# one-step heuristic from a generalized policy artifact.
#
# Usage:
#   bash scripts/baseline.sh <name>

set -e

cd /home/user

mkdir -p tmp
python -m baseline.one_step_imitation
python -m eval.evaluate_gripper --include-baseline --policy outputs/missing_policy.json --output tmp/baseline_scores.json
