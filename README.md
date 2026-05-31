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

The paper's code-release footnote points to
`https://github.com/bonetblai/learner-policies-from-examples`, verified on
2026-05-31 at commit `9991926f7655c4b6c8dc2f0404123639e42056f2`.

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
selected feature count, policy rule count, optional learning diagnostics, and
plan length ratio against the domain planner.

## Baselines and Targets

The paper reports that Gripper is solved with 100% large-instance coverage and
effective width 0. In the training table, Gripper uses one outer iteration, one
inner iteration, three selected features, and four policy rules.

## Evaluation Protocol

The reusable benchmark trains on five small Gripper instances with 1 through 5
balls and evaluates on thirty larger instances with 6 through 35 balls, matching
the paper's reported Gripper train/test counts. The evaluator reads a policy JSON
artifact written by a submitted solver and executes it independently using only the
problem dynamics in `data/`. Scores are written to `scoring/scores.json`.

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

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 2m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 07:18] - core_claim
- Continuing-agent audit inspected `method/`, `data/`, `eval/`, scripts, briefing, and scoring deliverables.
- Confirmed the implementation is GENEX/WRAPPER at Gripper scale: hitting-set feature selection, monotonicity chains, stratified projected policies, and wrapper validation are present.
- Re-ran `scripts/evaluate.sh`, `scripts/reproduce.sh`, and `python validate.py --compare`; all reproduced the same core-claim scores.

### [2026-05-31 07:07] - core_claim
- CPU compute job `98e1d2b9-b6a` completed `scripts/reproduce.sh` and `python validate.py --compare` successfully.
- GENEX plus WRAPPER learned a stratified Gripper policy with 3 selected features and 4 rules.
- Independent evaluation reports 100% training coverage, 100% large-instance coverage, and effective width 0 on held-out instances.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:17] - core_claim
- Continuing-agent audit found the implementation is a real scaled-down GENEX/WRAPPER reproduction, not a surrogate.
- Re-ran `scripts/reproduce.sh`, standalone `scripts/evaluate.sh`, and `python validate.py --compare`; all passed locally.
- Verified the one-step imitation baseline fails on held-out Gripper instances while GENEX reaches 100% held-out coverage, supporting the core generalization claim.

### [2026-05-31 07:18] - core_claim
- Completed CPU container job `86843c23-d46` on the corrected five-training/thirty-held-out Gripper split.
- The job regenerated `outputs/genex_gripper/policy.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare`.
- Reconfirmed the core claim with 100% train coverage, 100% held-out coverage, effective width 0, 3 selected features, and 4 policy rules.

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:17] - core_claim
- Continuing-agent audit found the implementation is a real scaled-down GENEX/WRAPPER reproduction, not a surrogate.
- Re-ran `scripts/reproduce.sh`, standalone `scripts/evaluate.sh`, and `python validate.py --compare`; all passed locally.
- Verified the one-step imitation baseline fails on held-out Gripper instances while GENEX reaches 100% held-out coverage, supporting the core generalization claim.

### [2026-05-31 07:18] - core_claim
- Completed CPU container job `86843c23-d46` on the corrected five-training/thirty-held-out Gripper split.
- The job regenerated `outputs/genex_gripper/policy.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare`.
- Reconfirmed the core claim with 100% train coverage, 100% held-out coverage, effective width 0, 3 selected features, and 4 policy rules.

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:17] - core_claim
- Continuing-agent audit found the implementation is a real scaled-down GENEX/WRAPPER reproduction, not a surrogate.
- Re-ran `scripts/reproduce.sh`, standalone `scripts/evaluate.sh`, and `python validate.py --compare`; all passed locally.
- Verified the one-step imitation baseline fails on held-out Gripper instances while GENEX reaches 100% held-out coverage, supporting the core generalization claim.

### [2026-05-31 07:18] - core_claim
- Completed CPU container job `86843c23-d46` on the corrected five-training/thirty-held-out Gripper split.
- The job regenerated `outputs/genex_gripper/policy.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare`.
- Reconfirmed the core claim with 100% train coverage, 100% held-out coverage, effective width 0, 3 selected features, and 4 policy rules.

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 3m | **GPU**: 0.0h
- **Jobs**: 5 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:17] - core_claim
- Continuing-agent audit found the implementation is a real scaled-down GENEX/WRAPPER reproduction, not a surrogate.
- Re-ran `scripts/reproduce.sh`, standalone `scripts/evaluate.sh`, and `python validate.py --compare`; all passed locally.
- Verified the one-step imitation baseline fails on held-out Gripper instances while GENEX reaches 100% held-out coverage, supporting the core generalization claim.

### [2026-05-31 07:18] - core_claim
- Completed CPU container job `86843c23-d46` on the corrected five-training/thirty-held-out Gripper split.
- The job regenerated `outputs/genex_gripper/policy.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare`.
- Reconfirmed the core claim with 100% train coverage, 100% held-out coverage, effective width 0, 3 selected features, and 4 policy rules.

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 2m | **GPU**: 0.0h
- **Jobs**: 5 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:17] - core_claim
- Continuing-agent audit found the implementation is a real scaled-down GENEX/WRAPPER reproduction, not a surrogate.
- Re-ran `scripts/reproduce.sh`, standalone `scripts/evaluate.sh`, and `python validate.py --compare`; all passed locally.
- Verified the one-step imitation baseline fails on held-out Gripper instances while GENEX reaches 100% held-out coverage, supporting the core generalization claim.

### [2026-05-31 07:18] - core_claim
- Completed CPU container job `86843c23-d46` on the corrected five-training/thirty-held-out Gripper split.
- The job regenerated `outputs/genex_gripper/policy.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare`.
- Reconfirmed the core claim with 100% train coverage, 100% held-out coverage, effective width 0, 3 selected features, and 4 policy rules.

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 5 total (5 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:17] - core_claim
- Continuing-agent audit found the implementation is a real scaled-down GENEX/WRAPPER reproduction, not a surrogate.
- Re-ran `scripts/reproduce.sh`, standalone `scripts/evaluate.sh`, and `python validate.py --compare`; all passed locally.
- Verified the one-step imitation baseline fails on held-out Gripper instances while GENEX reaches 100% held-out coverage, supporting the core generalization claim.

### [2026-05-31 07:18] - core_claim
- Completed CPU container job `86843c23-d46` on the corrected five-training/thirty-held-out Gripper split.
- The job regenerated `outputs/genex_gripper/policy.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare`.
- Reconfirmed the core claim with 100% train coverage, 100% held-out coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:35] - core_claim
- Verified the paper's released code repository URL from the recovered footnote: `https://github.com/bonetblai/learner-policies-from-examples`.
- Updated the default evaluator so `scoring/scores.json` includes the same benefit and constraint metrics defined in `scoring/reference.json`.
- Local rerun of `scripts/method.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` passed.

### [2026-05-31 07:45] - core_claim
- Final verification kept the milestone at `core_claim`.
- Tightened method-agnostic wording in evaluation and direction documentation for from-scratch gym use.
- Documented which reference metrics are paper-reported versus gym-derived, then re-ran `scripts/evaluate.sh` and `python validate.py --compare` successfully.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
