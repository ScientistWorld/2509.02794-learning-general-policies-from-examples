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
