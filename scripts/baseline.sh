#!/bin/bash
# Regenerate and score the gym's reference baselines.
#
# The evaluator owns fixed copies of these baseline policies and scores them on
# every slice (they appear in every scores file). This script rebuilds them from
# data/ for inspection and scores the rebuilt artifacts on the visible slice.
#
#   one_step_imitation  - imitates only the first plan action (pick)
#   plan_projection     - projects the five-ball example plan onto the named
#                         non-distractor features, no selection/simplification
#
# Usage:
#   bash scripts/baseline.sh

set -e

cd /home/user

for name in one_step_imitation plan_projection; do
    python -m "baseline.${name}"
    python -m eval.train.evaluate_gripper --no-baselines \
        --policy "tmp/baselines/${name}/policy.json" \
        --output "tmp/baselines/${name}/scores_train.json" > "tmp/baselines/${name}/eval.log"
    grep "^\[train\]" "tmp/baselines/${name}/eval.log"
done
