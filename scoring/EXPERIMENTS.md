# Experiment Overview

## gripper_generalization

Tests whether a compact generalized planning policy learned from small Gripper
examples solves both the training instances and a larger held-out suite. The
experiment also checks whether success comes from a direct policy with no extra
search assistance and whether the resulting representation stays compact. The
visible train-score script and hidden test-score script split the held-out suite
by alternating instance size; both also include disjoint capacity-shift cases.
