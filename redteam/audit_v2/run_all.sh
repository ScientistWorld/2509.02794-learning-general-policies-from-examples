#!/bin/bash
set -euo pipefail
cd /home/user
bash redteam/v2_reference_seed_0/run.sh
bash redteam/v2_reference_seed_1/run.sh
bash redteam/v2_reference_seed_2/run.sh
bash redteam/v2_better_learned_refinement/run.sh
bash redteam/v2_weaker_no_pick/run.sh
bash redteam/v2_weaker_lazy_one_ball/run.sh
bash redteam/v2_weaker_redundant_feature/run.sh
bash redteam/v2_shortcut_handwritten_reference/run.sh
bash redteam/v2_shortcut_handwritten_optimal/run.sh
bash redteam/v2_shortcut_forged_scores/run.sh
bash redteam/v2_shortcut_implicit_planner/run.sh
bash redteam/v2_shortcut_empty_output/run.sh
bash redteam/v2_shortcut_impossible_values/run.sh
bash redteam/v2_shortcut_undercount_features/run.sh
bash redteam/v2_shortcut_fixed_feature/run.sh
bash redteam/v2_shortcut_unknown_feature/run.sh
bash redteam/v2_shortcut_mutable_goal_and_size/run.sh
bash redteam/v2_shortcut_planner_denominator/run.sh
bash redteam/v2_shortcut_baseline_artifact/run.sh
bash redteam/v2_shortcut_test_answers/run.sh
bash redteam/v2_shortcut_copied_baseline/run.sh
bash redteam/v2_shortcut_no_artifact/run.sh
python -m redteam.audit_v2.summarize
