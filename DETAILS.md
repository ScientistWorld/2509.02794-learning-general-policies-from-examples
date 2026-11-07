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

---

# Evaluation

## What is evaluated

A submission is a policy artifact, `policy.json`, written anywhere under
`outputs/`, `checkpoints/` or `method_outputs/`. The method name is the name of
the directory that holds the artifact. The evaluator reads only two fields:

- `selected_features`: a list of feature names from the benchmark's named
  feature pool (the names in `data/gripper.py`'s `feature_pool(120)`: seven
  domain features plus `distractor_000` … `distractor_119`).
- `rules`: a list of rules, each with a `condition` (list of
  `[feature, "0" | "1"]`, meaning value zero/false or positive/true) and
  `effects` (list of `[feature, value]`). Numerical features take `up`, `down`,
  `same` or `any`. Boolean features take `true` (changes false→true), `false`
  (changes true→false), `same` or `any`. A selected feature that is not listed
  in a rule's effects must stay unchanged. Every feature a rule mentions must be
  selected.

Every other field is ignored. The evaluator never reads numbers, flags or
verdicts that the method wrote. It uses its own copy of the dynamics, the goal
test, the meaning of every feature name, the optimal plan lengths and the
instances. Editing `data/` does not change any score.

## How a policy is executed

A transition (s, t) is a policy transition if it is compatible with at least
one rule. A policy **solves** an instance only if *every* maximal policy
trajectory from the initial state is finite and ends in a goal state: the policy
must be closed (some admitted successor at every reachable non-goal state) and
acyclic. All admitted successors are explored, so successor order never helps.

## Validity constraint (structural termination)

The rule set must be terminating by its form, independent of the instance:

1. every rule must entail a change of some selected feature (`up`, `down`,
   `true` or `false`), and
2. the selected features must admit a ranking where each feature is either
   monotone over all rules (never both increased and decreased), or monotone
   over the rules that leave a set G of lower-ranked features unchanged, for
   each Boolean valuation of G (at most 2 features in G; an `any` effect counts
   as a possible increase and decrease).

A malformed artifact, an unknown feature name, a feature that is used but not
selected, or a rule set that fails this check scores as **failed**: zero
coverage and the worst value on every other metric.

## Metrics (`gripper_generalization`)

| Metric | Meaning |
|---|---|
| `large_instance_coverage` | fraction of larger held-out instances solved |
| `hard_instance_coverage` | coverage on the larger half of those instances |
| `capacity_shift_coverage` | coverage with gripper capacities absent from the learning instances |
| `initial_state_shift_coverage` | coverage from initial states unlike the learning instances (robot in B, balls already in B or already held) |
| `train_coverage` | coverage on the five learning instances (1–5 balls) |
| `policy_quality` (primary) | mean over large instances of optimal plan length ÷ expected trajectory length when an executor picks uniformly among admitted successors |
| `max_plan_length_ratio`, `avg_plan_length_ratio` | longest admitted trajectory ÷ optimal plan length (max, mean) over held-out instances |
| `max_effective_width`, `avg_effective_width` | 0 when the rules select a successor at every reachable non-goal state (direct policy, no search needed) |
| `selected_features`, `policy_rules` | size of the policy |
| `max_applicable_successors`, `avg_applicable_successors` | diagnostics only (coefficient 0) |

**Gate.** If a policy does not solve every instance of the slice, the coverages
are reported as measured, but every other metric is pinned to its worst value:
quality 0, width 1, plan ratio 3, 20 features, 40 rules. A policy that fails the
task therefore never outranks one that solves it. For solving policies, plan
ratios are capped at 3, features at 20 and rules at 40.

**Rank.** Methods are ranked by the sum over metrics of the coefficient in
`scoring/reference.json` times the improvement over the reference method.

## Slices

- `scripts/evaluate_train.sh` (and `scripts/evaluate.sh`) score every artifact
  on disk on the visible slice in `eval/train/`, writing
  `scoring/scores_train.json` (`scoring/scores.json`).
- `scripts/evaluate_test.sh` runs with no arguments. It scores every artifact on
  disk on hidden instances held only in `eval/test/`, writing
  `scoring/scores_test.json`.

Both slices have the same composition: 18 larger instances of mixed parity with
up to about 60 balls, four capacity-shift instances (capacity 3–5), four
initial-state-shift instances, and the five learning instances. The sizes,
capacities and initial states differ between the slices.

Both slices also score three fixed baselines owned by the evaluator:
`one_step_imitation` (repeats only the first plan action), `plan_projection` (the
five-ball example plan projected onto the named domain features, with no
abstraction) and `admit_all_legal` (admits every legal successor; invalid).

## Paper targets

The paper reports 100% large-instance coverage and effective width 0 for
Gripper, with 3 selected features and 4 rules.

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

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 7m | **GPU**: 0.0h
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

### [2026-05-31 07:49] - core_claim
- Added a tracked one-step imitation baseline implementation and made default evaluation report both GENEX and baseline scores.
- Aligned `TARGETS.md`, `CONSTRAINTS.md`, and `DIRECTION.md` with the hard-instance, capacity-shift, and branching metrics that are actually scored.
- Local `scripts/reproduce.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` all passed; submitting a CPU job for container verification.

### [2026-05-31 07:52] - core_claim
- Completed final verification without downgrading the milestone.
- Confirmed method/problem separation, download portability, train/test evaluator wiring, and scoring coefficients are suitable for the Gripper gym.
- Fixed a stale baseline-script comment and removed generated Python cache folders, then re-ran `python validate.py --compare` successfully.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 7m | **GPU**: 0.0h
- **Jobs**: 1 total (1 completed, 0 failed)

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

### [2026-05-31 07:49] - core_claim
- Added a tracked one-step imitation baseline implementation and made default evaluation report both GENEX and baseline scores.
- Aligned `TARGETS.md`, `CONSTRAINTS.md`, and `DIRECTION.md` with the hard-instance, capacity-shift, and branching metrics that are actually scored.
- Local `scripts/reproduce.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` all passed; submitting a CPU job for container verification.

### [2026-05-31 07:52] - core_claim
- Completed final verification without downgrading the milestone.
- Confirmed method/problem separation, download portability, train/test evaluator wiring, and scoring coefficients are suitable for the Gripper gym.
- Fixed a stale baseline-script comment and removed generated Python cache folders, then re-ran `python validate.py --compare` successfully.

</details>

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 21m | **GPU**: 0.0h
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

### [2026-05-31 07:35] - core_claim
- Verified the paper's released code repository URL from the recovered footnote: `https://github.com/bonetblai/learner-policies-from-examples`.
- Updated the default evaluator so `scoring/scores.json` includes the same benefit and constraint metrics defined in `scoring/reference.json`.
- Local rerun of `scripts/method.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` passed.

### [2026-05-31 07:45] - core_claim
- Final verification kept the milestone at `core_claim`.
- Tightened method-agnostic wording in evaluation and direction documentation for from-scratch gym use.
- Documented which reference metrics are paper-reported versus gym-derived, then re-ran `scripts/evaluate.sh` and `python validate.py --compare` successfully.

### [2026-05-31 07:49] - core_claim
- Added a tracked one-step imitation baseline implementation and made default evaluation report both GENEX and baseline scores.
- Aligned `TARGETS.md`, `CONSTRAINTS.md`, and `DIRECTION.md` with the hard-instance, capacity-shift, and branching metrics that are actually scored.
- Local `scripts/reproduce.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` all passed; submitting a CPU job for container verification.

### [2026-05-31 07:52] - core_claim
- Completed final verification without downgrading the milestone.
- Confirmed method/problem separation, download portability, train/test evaluator wiring, and scoring coefficients are suitable for the Gripper gym.
- Fixed a stale baseline-script comment and removed generated Python cache folders, then re-ran `python validate.py --compare` successfully.

### [2026-11-07] - core_claim (hardening)
- Gym hardened against the red-team report. Changes:
  - standard Gripper dynamics, scored with the paper's all-trajectories notion of solving;
  - a structural-termination gate (k-stratified, k <= 2);
  - evaluator-owned dynamics, features, optimal lengths, instances and baselines;
  - hidden test instances that exist only in `eval/test/`;
  - failure pinning.
- WRAPPER verification now explores every policy trajectory (Alg. 2, line 7).
  It still learns the paper's 3-feature / 4-rule Gripper policy in 1 outer and 1 inner iteration.
- CPU job `3fc1f5d3-2c7`:
  - the reference solves every hidden instance;
  - genuine refinement +0.082, lazy variant -0.147;
  - all shortcuts fail or have no effect;
  - seed spread 0.
  See `HARDENING.md`.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 3 total (3 completed, 0 failed)

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

### [2026-05-31 07:49] - core_claim
- Added a tracked one-step imitation baseline implementation and made default evaluation report both GENEX and baseline scores.
- Aligned `TARGETS.md`, `CONSTRAINTS.md`, and `DIRECTION.md` with the hard-instance, capacity-shift, and branching metrics that are actually scored.
- Local `scripts/reproduce.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` all passed; submitting a CPU job for container verification.

### [2026-05-31 07:52] - core_claim
- Completed final verification without downgrading the milestone.
- Confirmed method/problem separation, download portability, train/test evaluator wiring, and scoring coefficients are suitable for the Gripper gym.
- Fixed a stale baseline-script comment and removed generated Python cache folders, then re-ran `python validate.py --compare` successfully.

### [2026-11-07] - core_claim (hardening)
- Gym hardened against the red-team report. Changes:
  - standard Gripper dynamics, scored with the paper's all-trajectories notion of solving;
  - a structural-termination gate (k-stratified, k <= 2);
  - evaluator-owned dynamics, features, optimal lengths, instances and baselines;
  - hidden test instances that exist only in `eval/test/`;
  - failure pinning.
- WRAPPER verification now explores every policy trajectory (Alg. 2, line 7).
  It still learns the paper's 3-feature / 4-rule Gripper policy in 1 outer and 1 inner iteration.
- CPU job `3fc1f5d3-2c7`:
  - the reference solves every hidden instance;
  - genuine refinement +0.082, lazy variant -0.147;
  - all shortcuts fail or have no effect;
  - seed spread 0.
  See `HARDENING.md`.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
