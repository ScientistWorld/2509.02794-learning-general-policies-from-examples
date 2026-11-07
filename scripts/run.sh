#!/bin/bash
# End-to-end job (CPU, no internet).
#
# 1. Rebuilds the baselines and relearns the GENEX + WRAPPER reference on both
#    domains (outputs/genex_wrapper/{policy.json,childsnack_policy.json}).
# 2. Runs the hardening audit: the reference (three hash seeds), better and
#    weaker variants and shortcuts, each scored alone through
#    `bash scripts/evaluate_test.sh` (redteam/hardening_v3/results.json).
# 3. Regenerates scoring/scores*.json from the reference and baselines only,
#    and validates the workspace.

set -e

cd /home/user

rm -rf outputs
bash scripts/baseline.sh
bash scripts/method.sh
python -m redteam.hardening_v3.harness
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
python validate.py --post-design --compare
