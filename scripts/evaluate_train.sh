#!/bin/bash
# Visible train-slice evaluation for the Gripper research gym.
#
# Scores every policy artifact on disk (outputs/, checkpoints/, method_outputs/)
# plus the evaluator-owned baselines, and writes scoring/scores_train.json.
# Does not train or regenerate any method.

set -e

cd /home/user

mkdir -p scoring

python -m eval.train.evaluate "$@"
