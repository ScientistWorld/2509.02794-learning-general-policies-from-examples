# Experiment Overview

## gripper_generalization

Tests whether a compact rule-based policy learned from five small Gripper
examples is a genuinely general solution for the domain. The policy must solve
every instance in the hidden held-out suites, under every choice an executor
could make among the actions the policy allows:

- larger instances (with a harder top half),
- unseen gripper capacities,
- unseen initial situations,
- the learning instances themselves.

The experiment also checks that the policy is terminating by its form, acts
directly without search, and stays small. Among policies that solve
everything, it rewards trajectories that come close to optimal plan length.

A policy that is malformed, not structurally terminating, or does not solve
every instance cannot gain from compactness or efficiency: those metrics are
pinned to their worst values. The visible train slice (`eval/train/`) and the
hidden test slice (`eval/test/`) have the same composition with different sizes,
capacities and initial states.
