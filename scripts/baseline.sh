#!/bin/bash
# Regenerate and score the gym's reference baselines.
#
# The evaluator owns fixed copies of these baseline policies and scores them on
# every slice (they appear in every scores file). This script rebuilds them from
# data/ for inspection and scores the rebuilt artifacts on the visible slice
# (each rebuilt directory holds one domain's artifact, so the other domain shows
# as failed for it).
#
#   one_step_imitation        - Gripper: imitates only the first plan action (pick)
#   plan_projection           - Gripper: projects the five-ball example plan onto
#                               the named non-distractor features, no
#                               selection/simplification
#   childsnack_plan_projection - Childsnack: projects one example plan onto every
#                               named non-distractor feature, full conditions
#
# Usage:
#   bash scripts/baseline.sh

set -e

cd /home/user

python -m baseline.one_step_imitation
python -m baseline.plan_projection
python -m baseline.childsnack_plan_projection
python -m eval.train.evaluate --no-baselines \
    --method-dir tmp/baselines/one_step_imitation \
    --method-dir tmp/baselines/plan_projection \
    --method-dir tmp/baselines/childsnack_plan_projection \
    --output tmp/baselines/scores_train.json | grep "^\[train\]"
