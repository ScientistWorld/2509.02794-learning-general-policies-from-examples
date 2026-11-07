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
- The learned policies do not always generalize: the paper's Childsnack policy
  solves only 41.7% of its test instances (Table 3). This gym scores both a
  Gripper experiment (the reproduced core claim) and a Childsnack experiment
  (where the method falls short), with weight 0.5 each.

---

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

---

# Evaluation

## What is evaluated

A method is a directory under `outputs/`, `checkpoints/` or `method_outputs/`;
the method name is the directory name. It submits one policy artifact per
domain:

- `policy.json`: the Gripper policy (experiment `gripper_generalization`);
- `childsnack_policy.json`: the Childsnack policy (experiment
  `childsnack_generalization`).

A missing artifact scores that experiment as failed. The evaluator reads only
two fields of each artifact:

- `selected_features`: a list of feature names from that domain's named feature
  pool. These are the names in `feature_pool(120)` of `data/gripper.py` and of
  `data/childsnack.py`: the domain features plus `distractor_000` …
  `distractor_119`.
- `rules`: a list of rules. Each has a `condition`, a list of
  `[feature, "0" | "1"]` meaning value zero/false or positive/true, and
  `effects`, a list of `[feature, value]`. Numerical features take `up`,
  `down`, `same` or `any`. Boolean features take `true` (changes false→true),
  `false` (changes true→false), `same` or `any`. A selected feature that is not
  listed in a rule's effects must stay unchanged. Every feature a rule mentions
  must be selected.

Every other field is ignored. The evaluator never reads numbers, flags or
verdicts that the method wrote. For each domain it uses its own copy of the
dynamics, the goal test, the meaning of every feature name, the optimal plan
lengths and the instances. Editing `data/` does not change any score.

## How a policy is executed

A transition (s, t) is a policy transition if it is compatible with at least
one rule. A policy **solves** an instance only if *every* maximal policy
trajectory from the initial state is finite and ends in a goal state: the policy
must be closed (some admitted successor at every reachable non-goal state),
must never reach a dead end, and must be acyclic. All admitted successors are
explored, so successor order never helps.

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

## Experiment `gripper_generalization`

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

**Gate.** If a Gripper policy does not solve every instance of the slice, the
coverages are reported as measured, but every other metric is pinned to its
worst value: quality 0, width 1, plan ratio 3, 20 features, 40 rules. For
solving policies, plan ratios are capped at 3, features at 20 and rules at 40.

Both slices have the same composition: 18 larger instances of mixed parity with
up to about 60 balls, four capacity-shift instances (capacity 3–5), four
initial-state-shift instances, and the five learning instances.

## Experiment `childsnack_generalization`

Held-out instances come in three suites of 12:

- `size`: 4–9 children, with exactly sufficient resources, as in learning;
- `resource`: surplus bread, content or sandwich objects;
- `initial`: some sandwiches already made, in the kitchen or on the tray,
  and/or the tray starting at a table.

| Metric | Meaning |
|---|---|
| `heldout_coverage` (primary) | fraction of the 36 held-out instances solved |
| `size_coverage`, `resource_shift_coverage`, `initial_state_shift_coverage` | coverage on each suite |
| `train_coverage` | coverage on the ten learning instances |
| `policy_quality` | mean over held-out instances of optimal plan length ÷ expected trajectory length under uniform choice among admitted successors (0 for an unsolved instance) |
| `max_effective_width` | 1 if on some held-out instance the policy reaches a non-goal state that is not a dead end where it admits no successor (search would be needed) |
| `avg_effective_width` | mean over held-out instances of the fraction of such reachable states |
| `selected_features`, `policy_rules` | size of the policy (capped at 20 and 40) |

**Gate.** A Childsnack policy that does not solve all ten learning instances
counts as failed. Its coverages are reported as measured, and every other metric
is pinned to its worst value: quality 0, width 1, 20 features, 40 rules.
Partial held-out coverage is not a failure; it is what the experiment measures.

## Rank

Methods are ranked by the sum over experiments of the experiment's weight times
the sum over metrics of the metric's coefficient in `scoring/reference.json`
times the improvement over the reference method. The two experiments have
weight 0.5 each.

## Slices

- `scripts/evaluate_train.sh` (and `scripts/evaluate.sh`) score every method on
  disk on the visible slice in `eval/train/`. They write
  `scoring/scores_train.json` (`scoring/scores.json`).
- `scripts/evaluate_test.sh` runs with no arguments. It scores every method on
  disk on hidden instances held only in `eval/test/`, and writes
  `scoring/scores_test.json`.

The two slices have the same composition with different instances.

Every scores file also scores three fixed baselines owned by the evaluator, for
both domains:

- `one_step_imitation`: repeats only the first plan action;
- `plan_projection`: one example plan projected onto the named domain features,
  with no abstraction;
- `admit_all_legal`: admits every legal successor, which is invalid.

## Paper targets

The paper reports 100% large-instance coverage and effective width 0 for
Gripper, with 3 selected features and 4 rules. For Childsnack, its learned
policy (6 features, 8 rules) solves 41.7% of its 120 test instances, with
effective width up to 1.

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

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 1.1h | **GPU**: 0.0h
- **Jobs**: 6 total (5 completed, 0 failed)

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

### [2026-11-07] - core_claim (hardening, iteration 12)
- Added a second experiment, `childsnack_generalization`: the paper's domain
  where its learned policy falls short (Table 3: 41.7%).
  - Same GENEX + WRAPPER method; S1 fails and WRAPPER switches to S2, as in the
    paper.
  - Hidden test: the reference solves 19/36 held-out instances, with max
    effective width 1 (paper: 1.00).
- CPU job `93d0d57e-ed2` passed `validate.py`. Audit results:
  - learned Childsnack improvements +0.0525 and +0.0282;
  - weaker variants -0.46 and -0.87;
  - all Childsnack shortcuts fail;
  - Gripper ordering unchanged;
  - seed spread 0.
- Open issue: the hand-written Gripper policy still ties the learned refinement.
  This is a provenance issue left to the grader. See `HARDENING.md`.

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
