# Research Direction

## Research Problem

This benchmark studies generalized planning policies: compact rules that solve
families of classical planning instances rather than a single fixed instance.
The question is how to learn policies from small examples that still solve
larger instances.

## Core Contribution

The paper's contribution is symbolic policy learning from transition examples
with explicit termination and compactness guarantees. Improvements should remain
within this family of interpretable, feature-based generalized policies.

## Approach Scope

Scientists may improve feature selection, transition selection, wrapper repair
strategies, policy simplification, ranking/termination tests, or the scoring
heuristic used to choose features. The output must still be an executable
feature-rule policy over the benchmark dynamics.

## Out of Bounds

- Replacing the policy with a planner or search algorithm at evaluation time
- Training a neural controller that maps states to actions without feature-rule
  policy structure
- Memorizing all held-out states or using held-out instances during training
- Changing the Gripper dynamics, object capacity, or evaluation split
