#!/bin/bash
# Run the paper's proposed method (GENEX + WRAPPER) and score it.
#
# Writes outputs/genex_wrapper/policy.json (Gripper) and
# outputs/genex_wrapper/childsnack_policy.json (Childsnack), then runs the
# default evaluation on the visible slice.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

python -m method.run_genex
bash scripts/evaluate.sh
