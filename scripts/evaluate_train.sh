#!/bin/bash
# Visible train-slice evaluation for the Gripper research gym.
#
# Mirrors scripts/evaluate.sh: reads method artifacts and writes a scoring JSON.
# This script does not train or regenerate the method.

set -e

cd /home/user

mkdir -p scoring

python -m eval.train.evaluate_gripper "$@"
