#!/bin/bash
# End-to-end reproduction job (CPU, no internet).
#
# Rebuilds the baselines, relearns the GENEX + WRAPPER reference policy, scores
# every artifact on disk on the visible and hidden slices, and validates.
# The hardening audit (variants and shortcuts through the hidden test) can be
# rerun with: python -m redteam.hardening.harness

set -e

cd /home/user

rm -rf outputs/candidate
bash scripts/baseline.sh
bash scripts/method.sh
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
python validate.py --post-design --compare
