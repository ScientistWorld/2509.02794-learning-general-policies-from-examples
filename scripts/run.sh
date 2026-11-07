#!/bin/bash
# Hardening verification job (CPU, no internet).
#
# 1. Rebuild the baselines and relearn the reference policy from the final code.
# 2. Check that the learner is deterministic across hash seeds.
# 3. Run every better/weaker variant and every shortcut through the hidden test
#    (redteam/hardening/harness.py restores all files it touches).
# 4. Regenerate scoring/scores_train.json and scoring/scores_test.json from the
#    reference policy and the evaluator-owned baselines alone, then validate.

set -e

cd /home/user

rm -rf outputs/candidate
bash scripts/baseline.sh
bash scripts/method.sh
python -m redteam.hardening.seeds
python -m redteam.hardening.harness
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
python validate.py --post-design --compare
