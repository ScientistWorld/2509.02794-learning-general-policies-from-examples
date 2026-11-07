#!/bin/bash
set -euo pipefail
cd /home/user
for case in reference_seed_0 reference_seed_1 reference_seed_2 \
    better_direct_policy weaker_no_pick shortcut_implicit_planner \
    shortcut_test_answers shortcut_forged_scores shortcut_planner_denominator \
    shortcut_fixed_feature shortcut_mutable_goal shortcut_test_size \
    shortcut_empty_output shortcut_baseline_artifact shortcut_impossible_values; do
    bash "redteam/$case/run.sh"
done
python -m redteam.summarize
