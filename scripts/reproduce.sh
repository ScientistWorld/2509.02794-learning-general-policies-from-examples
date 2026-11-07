#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# Runs inside the compute container (working directory /home/user, no internet;
# no downloads are needed). Rebuilds the baselines, relearns the GENEX + WRAPPER
# Gripper policy (outputs/genex_wrapper/policy.json), and scores it on the
# visible and hidden slices.

set -e

cd /home/user

bash scripts/baseline.sh
bash scripts/method.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
