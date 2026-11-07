# Experiment Overview

The two experiments have weight 0.5 each.

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

## childsnack_generalization

Tests generalization in a domain with dead ends and limited resources. This is
the setting where policies learned from a few small examples are known to
break. The policy is learned from ten instances with three children each, where
every resource is exactly sufficient. It is then run on 36 hidden instances in
three suites:

- more children;
- surplus ingredients or sandwich objects;
- a different starting situation (sandwiches already made, the tray elsewhere).

The experiment measures how many of these instances the policy solves (every
allowed trajectory must reach the goal without wasting what allergic children
need). It also measures how close the policy's trajectories come to optimal
length, whether the policy ever gets stuck where a search would be needed, and
its size. The reference reaches full coverage on the size suite and only partial
coverage on the other two, so most of the room for improvement is here.

A policy that is malformed, not structurally terminating, or does not solve its
own learning instances is scored as failed. Both slices have the same
composition with different instances.
