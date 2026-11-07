#!/bin/bash
# Run the paper's proposed method (GENEX + WRAPPER) and score it.
#
# Writes outputs/genex_wrapper/policy.json, then runs the default evaluation.
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

python -m method.run_genex
bash scripts/evaluate.sh
