# Scientist Constraints

## Data

Gripper: learn only from the five Gripper training instances in
`data/gripper.py` (1 through 5 balls, two grippers). Childsnack: learn only from
the ten training instances in `data/childsnack.py` (three children each). You may
use each domain's dynamics, planner, feature pool, and any state reachable in
those training instances. Do not train or tune on the instances of the visible
evaluation slice in `eval/train/`; they are for validation. The hidden test
instances exist only in `eval/test/`.

## Policy Interface

For each method, write `policy.json` (Gripper) and `childsnack_policy.json`
(Childsnack) under `outputs/<method_name>/`, in the same format as the files in
`outputs/genex_wrapper/`. Use only feature names from that domain's pool. List
every feature the rules mention in `selected_features`. The evaluator defines
what each feature name means. Redefining a feature in `data/` changes nothing in
evaluation, except that your method then learns from values the evaluator does
not use. A missing artifact scores that experiment as failed.

## Validity

The rule set must be structurally terminating: every rule entails a feature
change, and the features admit a stratified ranking with at most two
conditioning features. See `briefing/evaluation.md`. Otherwise the run is
scored as failed.

## Resource Scale

Keep the same action dynamics and benchmark generators. Do not call a planner or
a search procedure during evaluation; the artifact must be the policy itself.

## Compliance Checklist

- [ ] Gripper training uses only the five 1 through 5 ball instances
- [ ] Childsnack training uses only the ten 3-children instances (and states reachable in them)
- [ ] Both policy files can be scored by `scripts/evaluate.sh`
- [ ] Only pool feature names are used, and all of them are listed as selected
- [ ] Both rule sets are structurally terminating
- [ ] Policies are learned from the training data, not written by hand
- [ ] No planner call or external search is part of a submitted policy
