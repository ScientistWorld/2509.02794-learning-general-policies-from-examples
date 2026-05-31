# Problem Definition

## Research Question

Learn a single generalized planning policy that solves a family of related
classical planning instances, rather than solving each instance independently.
The policy must choose valid state transitions for unseen instances in the same
domain and should continue to work when the number of objects is larger than in
the training examples.

## Why It Matters

Generalized planning policies are reusable and interpretable. A good policy can
replace repeated search on every new instance with a compact rule set that can be
inspected, tested, and applied across a whole domain.

## Success Criteria

A successful system learns a compact rule-based policy from small example
instances, solves all training instances, generalizes to larger held-out
instances, and avoids infinite trajectories or search assistance whenever the
policy is meant to act directly.
