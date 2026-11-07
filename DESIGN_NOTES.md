# Design Notes

## Checked

- Read `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` side by side. They dispatch to separate train/test evaluator modules and write through those modules to `scoring/scores_train.json` and `scoring/scores_test.json`.
- Checked `eval/train/` and `eval/test/` for cross-import leakage. They remain duplicated rather than importing from each other.
- Checked `scoring/reference.json` for paper-agreement metrics. None were present.
- Checked that `scoring/scores_train.json` and `scoring/scores_test.json` do not exist.
- Ran `bash -n` on both train/test wrapper scripts and JSON validation on `scoring/reference.json`.

## Changed

- Added `hard_instance_coverage` to both slices so a policy that only handles the easier visible large cases is separated from one that generalizes across the larger part of the slice.
- Added same-domain capacity-shift cases to both slices. Train uses visible capacity-shift instances, while test uses different held-out capacities and ball counts.
- Added `max_applicable_successors` and `avg_applicable_successors`, computed from the policy's actual matched legal successors at visited states. This catches broad rule sets that solve only because evaluator successor ordering picks a good action.
- Added `avg_plan_length_ratio` alongside the existing max ratio to make action efficiency less dependent on a single worst case.
- Added top-level `slice` markers to train/test score payloads.
- Updated `scoring/reference.json` with descriptions for every metric.
- Set self-reported method stats (`feature_pool`, `inner_iterations`, `outer_iterations`, `hit_constraints`) to coefficient `0.0`. They remain diagnostic but no longer reward values a future method could forge in `policy.json`.

## Runtime Concerns For The Runner

- The new branching metrics may penalize nondeterministic-but-still-valid generalized policies that admit more than one progress action at a state. This is intentional as an anti-shortcut signal, but the runner should inspect whether it overwhelms coverage in aggregate scoring.
- Capacity-shift instances are lightweight and use the same Gripper transition system, but the runner should confirm the current reproduced policy still gets non-saturated, interpretable values on train and test.
- The train/test evaluators still read `policy.json` artifacts from `outputs/`, `checkpoints/`, or `method_outputs/`. A future method must emit that interface or pass `--policy`.

## Hardening Update (iteration 11)

The runtime concerns above are resolved; see `HARDENING.md`.

- Branching metrics are diagnostics with coefficient 0. Under all-trajectories
  semantics, extra admitted successors matter only through coverage and plan
  length.
- Both evaluators no longer read `data/`.
- The test slice scores every artifact on disk and does not consult
  `scores_train.json`.
