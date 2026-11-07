# Problem Definition

## Research Question

Learn a single generalized planning policy that solves a family of related
classical planning instances, rather than solving each instance independently.
The policy must choose valid state transitions for unseen instances in the same
domain. It should keep working when there are more objects than in the
learning examples, when resources differ, and when an instance starts from a
different situation.

The benchmark has two domains. A method learns one policy per domain.

**Gripper.** A robot with several grippers must carry every ball from room A to
room B. Moving between rooms is always possible, and a ball can be picked up or
dropped in either room. Learning uses five small instances (1 to 5 balls, two
grippers, everything starting in room A).

**Childsnack.** Sandwiches must be made in a kitchen from bread and content
portions, put on a tray, carried to the tables where children wait, and served.
Some children are allergic to gluten and may only be served gluten-free
sandwiches, which need gluten-free bread and gluten-free content. Any sandwich
can be made from any ingredients, but only one made from gluten-free ingredients
with the gluten-free action is gluten-free. The tray can move between the
kitchen and three tables. Ingredients and sandwich objects are limited, so
wasting gluten-free food can make an instance unsolvable (a dead end). Learning
uses ten instances with three children each, in which every resource is exactly
sufficient.

## Why It Matters

Generalized planning policies are reusable and interpretable. A good policy can
replace repeated search on every new instance with a compact rule set that can be
inspected, tested, and applied across a whole domain.

## Success Criteria

A successful system learns, for each domain, a compact rule-based policy over the
benchmark's named state features. The policy must:

- solve all learning instances and as many held-out instances as possible.
  Solving means every policy trajectory reaches the goal, with no dependence on
  which admitted action an executor happens to choose;
- be terminating by its structure, so that it cannot loop on any instance;
- act directly (width 0), with no search to find the next state;
- keep trajectories close to optimal plan length.
