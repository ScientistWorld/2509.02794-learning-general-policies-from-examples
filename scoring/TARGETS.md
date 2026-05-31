# Evaluation Targets

## Primary: gripper_generalization

Tests whether a learned policy solves thirty held-out Gripper instances that are
larger than the five examples used during learning.
- **Metric:** `large_instance_coverage` (higher is better)

## Constraint: direct_policy_behavior

Tests whether the learned object acts as a direct policy without needing search
to find a compatible successor.
- **Metric:** `max_effective_width` and `avg_effective_width` (lower is better)

## Constraint: compact_policy

Tests whether the solution remains a compact symbolic policy rather than growing
by memorizing many transitions.
- **Metric:** `selected_features`, `policy_rules`, and `max_plan_length_ratio`
  (lower is better)
