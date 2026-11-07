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

- **Childsnack generalization (most of the room).** The reference learns from
  ten small instances in which every resource is exactly sufficient. It solves
  every larger instance of that kind. It fails most instances with surplus
  resources and most instances that start with sandwiches already made or the
  tray at a table: there it gets stuck or wastes food that allergic children
  need. Overall it solves a bit over half of the held-out instances. A better
  learner extracts rules that stay correct off the situations seen in the
  example plans, while keeping structural termination.
- **Gripper efficiency.** The reference solves every held-out Gripper instance,
  so coverage is at its upper bound. It still allows trajectories that are much
  longer than optimal: worst case about 1.64 times the optimal length, expected
  quality about 0.90. Policies whose allowed trajectories are near-optimal
  score higher, if the rule set does not grow more than the gain is worth.

## Approach Scope

Scientists may improve how examples are chosen, how features are selected from
the benchmark pool, how rules are formed and refined, and how validity is
checked during learning. The output must still be an executable feature-rule
policy over the benchmark's named features, for each domain.

## Out of Bounds

- Replacing the policy with a planner or search algorithm at evaluation time
- Training a neural controller that maps states to actions without feature-rule
  policy structure
- Hand-writing a policy, or hand-editing a learned one, instead of learning it
  from the training examples
- Using held-out or validation instances during training
- Changing the dynamics, the feature semantics, or the evaluation code
