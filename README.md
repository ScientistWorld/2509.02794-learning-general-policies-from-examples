# Overview

- **Paper ID:** 2509.02794
- **Title:** Learning General Policies From Examples
- **Domain:** Symbolic AI planning / generalized planning
- **TL;DR:** The paper learns compact rule-based planning policies from example
  plans using a hitting-set algorithm with built-in structural termination.

## Short Summary

The paper targets generalized planning: learning one policy that solves a whole
family of planning instances. It replaces earlier SAT/ASP policy learners with
GENEX, a greedy hitting-set method that selects features and preserves
stratified termination. A WRAPPER procedure supplies positive and negative
transitions from planner rollouts until the policy is closed and safe on the
training set.

## Key Results

- The paper reports policies for 20 of 34 evaluated planning domains.
- Gripper is solved in the paper with one outer and one inner WRAPPER iteration,
  three selected features, four rules, and 100% large-instance coverage.
- Many learned policies retain effective width 0 on larger instances, meaning
  they act as direct policies rather than sketches needing additional search.

---

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

---

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

## Main Claims

The primary claim is that the GENEX plus WRAPPER pipeline can learn terminating,
interpretable generalized policies from small examples and large feature pools.
The paper also claims the learned policies generalize to larger instances in
many domains, often with effective width 0, and that failures are diagnosable as
feature expressivity limits or timeouts.

---

# Evaluation

## Metrics

The main metric is coverage: the fraction of instances solved by executing the
learned policy from the initial state until a goal is reached. Training coverage
checks whether the learner solved the examples it was given; large-instance
coverage checks generalization.

Effective width measures whether the learned object acts as a direct policy or
needs extra search. Width 0 is best and means the policy selects an applicable
successor directly. The evaluator also records compactness constraints:
selected feature count, policy rule count, wrapper iteration counts, and plan
length ratio against the domain planner.

## Baselines and Targets

The paper reports that Gripper is solved with 100% large-instance coverage and
effective width 0. In the training table, Gripper uses one outer iteration, one
inner iteration, three selected features, and four policy rules.

## Evaluation Protocol

The reusable benchmark trains on small Gripper instances and evaluates on larger
instances with more balls. The evaluator reads a policy JSON artifact written by
the method and executes it independently using only the problem dynamics in
`data/`. Scores are written to `scoring/scores.json`.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 15m | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

<!-- Write your progress here -->

</details>

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `none` | **Status**: error
- **Working time**: 30m | **GPU**: 0.0h

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 12m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 00:00] - none
- Read the paper markdown and identified GENEX, WRAPPER, stratified policies,
  coverage, and effective width as the core reproduction targets.
- Confirmed the workspace was scaffold-only.

### [2026-05-31 00:00] - method_runs
- Implemented a self-contained Gripper benchmark and feature pool.
- Implemented GENEX as a greedy hitting-set learner with stratification chains
  and WRAPPER-style transition seeding.
- Ran the method locally on the lightweight benchmark and produced a policy
  artifact plus `scoring/scores.json`.

### [2026-05-31 00:00] - core_claim
- Added the paper's optional policy simplification pass with checks that the
  simplified rule set remains stratified and solves the wrapper validation
  instances.
- Reproduced the paper's Gripper core result on the packaged benchmark:
  100% train coverage, 100% large-instance coverage, effective width 0, three
  selected features, and four policy rules.
- `python validate.py --compare` passes with independent evaluation.
- CPU container job `98e1d2b9-b6a` completed with exit code 0 and reproduced
  the same scores through `scripts/run.sh`.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
