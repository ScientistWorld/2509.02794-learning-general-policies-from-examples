# Problem Definition

## Research Question

Learn a single generalized planning policy that solves a family of related
classical planning instances, rather than solving each instance independently.
The policy must choose valid state transitions for unseen instances in the same
domain. It should keep working when the number of objects is larger than in the
training examples, when a resource such as the number of grippers changes, and
when the instance starts from a different situation.

The benchmark domain is Gripper. A robot with several grippers must carry every
ball from room A to room B. Moving between rooms is always possible, and a ball
can be picked up or dropped in either room. Learning uses five small instances
(1 to 5 balls, two grippers, everything starting in room A).

## Why It Matters

Generalized planning policies are reusable and interpretable. A good policy can
replace repeated search on every new instance with a compact rule set that can be
inspected, tested, and applied across a whole domain.

## Success Criteria

A successful system learns a compact rule-based policy over the benchmark's
named state features. The policy must:

- solve all training instances and all held-out instances, meaning every policy
  trajectory reaches the goal, with no dependence on which admitted action an
  executor happens to choose;
- be terminating by its structure, so that it cannot loop on any instance;
- act directly (width 0), with no search to find the next state;
- keep trajectories close to optimal plan length.
