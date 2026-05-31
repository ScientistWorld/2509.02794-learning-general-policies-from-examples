# Evaluation Targets

## Primary: gripper_generalization

Tests whether a learned policy solves thirty held-out Gripper instances that are
larger than the five examples used during learning.
- **Metric:** `policy_quality` (higher is better), with
  `large_instance_coverage` as the paper-facing coverage component.

## Robustness: held_out_variants

Tests whether the policy still works on harder held-out Gripper sizes and on
capacity variants that use the same transition rules but were not present in the
five training examples.
- **Metric:** `hard_instance_coverage` and `capacity_shift_coverage` (higher is
  better)

## Constraint: direct_policy_behavior

Tests whether the learned object acts as a direct policy without needing search
to find a compatible successor.
- **Metric:** `max_effective_width`, `avg_effective_width`,
  `max_applicable_successors`, and `avg_applicable_successors` (lower is better)

## Constraint: compact_policy

Tests whether the solution remains a compact symbolic policy rather than growing
by memorizing many transitions.
- **Metric:** `selected_features`, `policy_rules`, and `max_plan_length_ratio`
  / `avg_plan_length_ratio` (lower is better)
