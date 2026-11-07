# Research Direction

## Research Problem

This benchmark studies generalized planning policies: compact rules that solve
families of classical planning instances rather than a single fixed instance.
The question is how to learn, from a few small examples, policies that are
correct on much larger and differently configured instances. Correct here means
every trajectory the policy allows reaches the goal. The policies must also be
terminating by their form.

## Core Contribution

The paper's contribution is symbolic policy learning from example plans, with
explicit structural termination and compactness. Improvements should remain
within this family of interpretable, feature-based generalized policies.

## Where There Is Room

The reference policy solves every held-out instance, so coverage is at its
upper bound. It still allows trajectories that are much longer than optimal:
its worst case is about 1.64 times the optimal length, and its expected quality
is about 0.90. A better learner keeps full coverage and structural termination
while producing policies whose allowed trajectories are near-optimal. It should
also not grow the rule set more than that gain is worth.

## Approach Scope

Scientists may improve how examples are chosen, how features are selected from
the benchmark pool, how rules are formed and refined, and how validity is
checked during learning. The output must still be an executable feature-rule
policy over the benchmark's named features.

## Out of Bounds

- Replacing the policy with a planner or search algorithm at evaluation time
- Training a neural controller that maps states to actions without feature-rule
  policy structure
- Hand-writing the policy instead of learning it from the training examples
- Using held-out or validation instances during training
- Changing the Gripper dynamics, the feature semantics, or the evaluation code
