#!/bin/bash
# Held-out test-slice evaluation for the Gripper research gym.
#
# Mirrors scripts/evaluate.sh: reads method artifacts and writes a scoring JSON.
# By default, it scores every method key found in scoring/scores_train.json.

set -e

cd /home/user

mkdir -p scoring

python -m eval.test.evaluate_gripper --include-baseline "$@"
