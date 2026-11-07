#!/bin/bash
# Held-out test-slice evaluation for the Gripper research gym.
#
# Runs with no arguments: scores every policy artifact on disk (outputs/,
# checkpoints/, method_outputs/) plus the evaluator-owned baselines on the
# hidden instances in eval/test/, and writes scoring/scores_test.json.
# Does not train or regenerate any method.

set -e

cd /home/user

mkdir -p scoring

python -m eval.test.evaluate "$@"
