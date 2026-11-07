# Evaluation Targets

All targets are metrics of the single experiment `gripper_generalization`.
The evaluator recomputes all of them from the policy artifact.

## Primary: generalization to larger instances

Tests whether the policy solves larger held-out Gripper instances (every policy
trajectory must reach the goal) and how close its trajectories are to optimal.
- **Metrics:** `policy_quality` (primary, higher is better) and
  `large_instance_coverage` (paper-facing coverage, higher is better).

## Robustness: held-out variants

Tests the harder half of the large instances, unseen gripper capacities, and
unseen initial situations, all with the same transition rules.
- **Metrics:** `hard_instance_coverage`, `capacity_shift_coverage`,
  `initial_state_shift_coverage` (higher is better).

## Constraint: training task retained

- **Metric:** `train_coverage` (higher is better).

## Constraint: structural termination (gate)

The rule set must be terminating by its form (k-stratified, k ≤ 2, and every
rule entails a feature change). A violation scores the run as failed on every
metric. There is no separate metric.

## Constraint: direct policy behaviour

Tests whether the policy selects a successor at every reachable non-goal state,
with no search needed.
- **Metrics:** `max_effective_width`, `avg_effective_width` (lower is better).
- **Diagnostics (coefficient 0):** `max_applicable_successors`,
  `avg_applicable_successors`.

## Constraint: compact, efficient policy

Tests whether the policy stays small and avoids admitting needlessly long
trajectories.
- **Metrics:** `selected_features`, `policy_rules`, `max_plan_length_ratio`,
  `avg_plan_length_ratio` (lower is better).

If the policy does not solve every instance of a slice, every metric except the
coverages is pinned to its worst value.
