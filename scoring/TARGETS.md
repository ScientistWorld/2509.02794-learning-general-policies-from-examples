# Evaluation Targets

The evaluator recomputes every metric from the policy artifacts. Experiment
weights: `gripper_generalization` 0.5, `childsnack_generalization` 0.5.

## Experiment `gripper_generalization`

### Primary: generalization to larger instances

Tests whether the policy solves larger held-out Gripper instances (every policy
trajectory must reach the goal) and how close its trajectories are to optimal.
- **Metrics:** `policy_quality` (primary, higher is better) and
  `large_instance_coverage` (paper-facing coverage, higher is better).

### Robustness: held-out variants

Tests the harder half of the large instances, unseen gripper capacities, and
unseen initial situations, all with the same transition rules.
- **Metrics:** `hard_instance_coverage`, `capacity_shift_coverage`,
  `initial_state_shift_coverage` (higher is better).

### Constraint: training task retained

- **Metric:** `train_coverage` (higher is better).

### Constraint: direct policy behaviour

Tests whether the policy selects a successor at every reachable non-goal state,
with no search needed.
- **Metrics:** `max_effective_width`, `avg_effective_width` (lower is better).
- **Diagnostics (coefficient 0):** `max_applicable_successors`,
  `avg_applicable_successors`.

### Constraint: compact, efficient policy

Tests whether the policy stays small and avoids admitting needlessly long
trajectories.
- **Metrics:** `selected_features`, `policy_rules`, `max_plan_length_ratio`,
  `avg_plan_length_ratio` (lower is better).

If the policy does not solve every instance of a slice, every metric except the
coverages is pinned to its worst value.

## Experiment `childsnack_generalization`

### Primary: held-out coverage

Fraction of the 36 held-out Childsnack instances the policy solves. This is the
quantity the paper reports for its Childsnack test set.
- **Metric:** `heldout_coverage` (primary, higher is better).

### Robustness: per-suite coverage

Coverage on larger instances, on instances with surplus resources, and on
instances that start from a different situation.
- **Metrics:** `size_coverage`, `resource_shift_coverage`,
  `initial_state_shift_coverage` (higher is better).

### Efficiency

- **Metric:** `policy_quality`: optimal ÷ expected trajectory length, 0 for
  unsolved instances (higher is better).

### Constraint: training task retained

- **Metric:** `train_coverage` (higher is better). Below 1, the run counts as
  failed on every non-coverage metric.

### Constraint: direct policy behaviour

- **Metrics:** `max_effective_width`, `avg_effective_width` (lower is better).

### Constraint: compactness

- **Metrics:** `selected_features`, `policy_rules` (lower is better, small
  coefficients).

## Constraint for both experiments: structural termination (gate)

The rule set must be terminating by its form: k-stratified with k ≤ 2, and every
rule entails a feature change. A violation, a malformed or missing artifact, or
an unknown feature scores the experiment as failed on every metric. There is no
separate metric.
