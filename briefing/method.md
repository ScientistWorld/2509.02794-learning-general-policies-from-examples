# Paper's Method

## Key Contribution

The paper introduces a symbolic learner for generalized planning policies that
scales beyond earlier SAT/ASP encodings. Its central algorithm, GENEX, learns
features through a greedy min-cost hitting set procedure while enforcing a
structural termination condition.

## Approach

The learner starts from planner-generated example transitions. GENEX builds
hitting-set constraints that require selected features to change on good
transitions, distinguish good transitions from bad transitions, and separate
goal from non-goal states. When a feature is selected, the algorithm adds its
minimum-cost monotonicity chain so the projected policy is stratified and thus
acyclic by construction.

WRAPPER repeatedly calls GENEX. It executes the projected policy on training
instances, adds planner-recommended transitions when the policy is undefined,
and adds bad transitions when a policy step reaches a dead end. The outer loop
tests candidate policies over the full training collection.

The paper's code-release footnote points to
`https://github.com/bonetblai/learner-policies-from-examples`, verified on
2026-05-31 at commit `9991926f7655c4b6c8dc2f0404123639e42056f2`.

## This Reproduction

`method/genex.py` implements one domain-independent learner, run on both
domains by `method/run_genex.py`:

- **GENEX:** greedy min-cost hitting set, with minimum-cost monotonicity chains
  and an acyclic ordering constraint.
- **Projection:** good transitions are projected onto the selected features.
- **Simplification (optional, Alg. 2 line 6), inside the inner loop:** rule
  conditions are removed greedily, as in the paper's "simplify only conditions"
  configuration, under the paper's invariant. That invariant is: the same
  conditional monotonicities (hence stratified under the same ranking), and no
  bad transition admitted. Edits must also keep the policy solving Q′.
- **WRAPPER:** per-instance X+_P / X−_P that persist across outer iterations.
  It starts with strategy S1 and switches to strategy S2 when S1 fails, as in
  the paper's experiments. As in Algorithm 2, line 7, the WRAPPER test explores
  every policy trajectory. When it finds a reachable alive state with no policy
  transition, it adds the planner's transition from that state to X+. When it
  finds a policy transition into a dead end, it adds that transition to X−.

**Domains.** Both domains are hand-coded abstractions (counts instead of
objects) with standard STRIPS dynamics, not DLPLAN/TARSKI:

- **Gripper:** a 127-feature named pool and a greedy optimal planner. WRAPPER
  succeeds with S1 in one outer and one inner iteration: 3 features, 4 rules.
- **Childsnack:** the paper's ten 3-children training instances (Table 1:
  |Q| = 10), a 148-feature description-logic-style pool and a breadth-first
  optimal planner. S1 fails (GENEX finds no stratified hitting set for one
  singleton Q′). S2 returns a policy that solves all ten training instances
  after 9 outer iterations, with 12 features and 15 rules.

## Main Claims

The primary claim is that the GENEX plus WRAPPER pipeline can learn terminating,
interpretable generalized policies from small examples and large feature pools.
The paper also claims the learned policies generalize to larger instances in
many domains, often with effective width 0, and that failures are diagnosable as
feature expressivity limits or timeouts. Its own test shows limits: the
Childsnack policy solves only 41.7% of its test instances.
