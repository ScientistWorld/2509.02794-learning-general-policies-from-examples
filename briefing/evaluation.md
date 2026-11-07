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
