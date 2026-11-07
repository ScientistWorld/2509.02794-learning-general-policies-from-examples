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

`method/genex.py` implements GENEX (greedy min-cost hitting set with
minimum-cost monotonicity chains and an acyclic ordering constraint), the
projection of good transitions onto the selected features, the optional greedy
simplification (rules stay stratified and avoid bad transitions), and WRAPPER
with strategy S1. As in Algorithm 2, line 7, the WRAPPER test explores every
policy trajectory. When it finds a reachable alive state with no policy
transition, it adds the planner's transition from that state to X+. When it
finds a policy transition into a dead end, it adds that transition to X-. The
domain is a hand-coded abstract Gripper with standard STRIPS dynamics and a
127-feature named pool, not DLPLAN/TARSKI.

## Main Claims

The primary claim is that the GENEX plus WRAPPER pipeline can learn terminating,
interpretable generalized policies from small examples and large feature pools.
The paper also claims the learned policies generalize to larger instances in
many domains, often with effective width 0, and that failures are diagnosable as
feature expressivity limits or timeouts.
