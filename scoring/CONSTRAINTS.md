# Scientist Constraints

## Data

Learn only from the five Gripper training instances in `data/gripper.py`
(1 through 5 balls, two grippers). You may use the domain dynamics, the planner
and the feature pool in `data/gripper.py`. Do not train or tune on the instances
of the visible evaluation slice in `eval/train/`; they are for validation. The
hidden test instances exist only in `eval/test/`.

## Policy Interface

Write a policy artifact `policy.json` under `outputs/<method_name>/`, in the
same format as `outputs/genex_wrapper/policy.json`. Use only feature names from
the benchmark pool: the seven domain features and `distractor_000` …
`distractor_119`. List every feature the rules mention in `selected_features`.
The evaluator defines what each feature name means. Redefining a feature in
`data/` changes nothing in evaluation, except that your method then learns from
values the evaluator does not use.

## Validity

The rule set must be structurally terminating: every rule entails a feature
change, and the features admit a stratified ranking with at most two
conditioning features. See `briefing/evaluation.md`. Otherwise the run is
scored as failed.

## Resource Scale

Keep the same action dynamics and benchmark generator. Do not call a planner or
a search procedure during evaluation; the artifact must be the policy itself.

## Compliance Checklist

- [ ] Training uses only the five 1 through 5 ball instances
- [ ] Policy JSON can be scored by `scripts/evaluate.sh`
- [ ] Only pool feature names are used, and all of them are listed as selected
- [ ] The rule set is structurally terminating
- [ ] No planner call or external search is part of the submitted policy
