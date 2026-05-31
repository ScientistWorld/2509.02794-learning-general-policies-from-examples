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

Scientists may improve how examples are chosen, how the benchmark-provided
state features are selected, how rules are formed, and how policy validity is
checked. The output must still be an executable feature-rule policy over the
benchmark dynamics and feature names known to `data/gripper.py`.

## Out of Bounds

- Replacing the policy with a planner or search algorithm at evaluation time
- Training a neural controller that maps states to actions without feature-rule
  policy structure
- Memorizing all held-out states or using held-out instances during training
- Changing the Gripper dynamics, evaluator-defined capacities, or evaluation split
