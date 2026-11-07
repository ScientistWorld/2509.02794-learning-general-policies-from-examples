# Progress

## What Works

- Implemented the paper's actual core algorithmic pipeline at Gripper scale:
  GENEX hitting-set feature selection, monotonicity chains for stratification,
  projected feature-rule policies, and a WRAPPER-style learner seeded from
  planner transitions.
- `scripts/method.sh` writes `outputs/genex_gripper/policy.json`.
- `scripts/evaluate.sh` independently executes the policy and writes
  `scoring/scores.json`.
- The simplification pass removes redundant conditions and stable effects while
  preserving stratification, matching the paper's compact Gripper rule count.
- Continuing-agent audit confirmed that `eval/` does not import from `method/`,
  the scores are regenerated from the policy artifact, and the scripts remain
  functional as standalone deliverables.

## Results

- Local smoke test and CPU container job `98e1d2b9-b6a` reproduced the Gripper
  core claim on the generated benchmark: 100% training coverage, 100%
  large-instance coverage, max effective width 0, and average effective width 0.
- The learned policy uses 3 selected features and 4 rules, matching the paper's
  reported Gripper counts. It uses a smaller feature pool than the paper
  because the public code/data URL is missing from the provided markdown.
- Audit rerun on 2026-05-31 regenerated the same scores via
  `scripts/reproduce.sh` and passed `python validate.py --compare`.
- Updated the benchmark split to five Gripper training instances and thirty
  larger held-out instances, matching the paper's reported Gripper train/test
  counts more closely. CPU container job `86843c23-d46` reran the full pipeline
  on this corrected split and passed `python validate.py --compare`.
- Continuing audit on 2026-05-31 confirmed that `method/` implements recognizable
  GENEX/WRAPPER computational steps rather than a surrogate, `eval/` remains
  independent from `method/`, and standalone evaluation works. The one-step
  imitation baseline scores 0% large-instance coverage, while GENEX scores 100%.
- The recovered footnote code URL was verified with `git ls-remote` at
  `https://github.com/bonetblai/learner-policies-from-examples`, commit
  `9991926f7655c4b6c8dc2f0404123639e42056f2`.
- The default evaluator now reports all benchmark constraint metrics in
  `scoring/scores.json`: hard-instance coverage, capacity-shift coverage,
  applicable-successor branching, and average plan-length ratio. Local
  validation passed after regenerating the policy and all score files.
- The default evaluation now includes a runnable one-step imitation baseline
  from `baseline/`, and `scripts/reproduce.sh` exercises both the baseline and
  GENEX paths before validation. Local validation passed after this packaging
  cleanup.

## Hardening (iteration 11)

- Evaluation semantics follow the paper. A policy solves an instance only if
  every maximal policy trajectory reaches the goal, under standard Gripper
  dynamics. The rule set must be k-stratified (k <= 2).
- `eval/train/` and `eval/test/` are self-contained and own:
  - the dynamics and goal test;
  - feature semantics, BFS optimal plan lengths, instances and baselines.
- `data/` no longer exposes held-out instances.
- Results of job `3fc1f5d3-2c7` (details in `HARDENING.md`):
  - hidden-test reference: coverage 1 on every suite, quality 0.9004,
    worst-case plan ratio 1.64, 3 features / 4 rules;
  - `plan_projection` baseline: 50% large coverage.

## Hardening (iteration 12)

- Added `childsnack_generalization` (weight 0.5, Gripper 0.5).
  - The domain is the paper's Childsnack, where the learned policy falls short.
    It has ten 3-children training instances, real dead ends and a
    148-feature pool.
  - Evaluators `eval/{train,test}/evaluate_childsnack.py` are self-contained.
  - Hidden suites: size, resource surplus, shifted initial situation.
- The WRAPPER loop is domain-generic; Gripper behaviour is unchanged.
- Results of job `93d0d57e-ed2`:
  - Childsnack reference: 19/36 held-out on the hidden test, 21/36 on the
    visible slice;
  - learned variants that add training-reachable starts rank higher
    (+0.0525, +0.0282);
  - weaker variants and every shortcut rank lower;
  - `validate.py` passed.
  Details in `HARDENING.md`.
- The audit harness (`redteam/hardening_v3/`) runs as part of `scripts/run.sh`
  (about 50 min on one CPU).

## Remaining

- The packaged environment is complete for both experiments: method,
  evaluation, scoring targets, constraints, audit and end-to-end scripts are
  present.
- Optional future work: more paper domains (Delivery, Ferry), or a port to
  DLPLAN/TARSKI so the feature pool can grow.

## Issues

- The paper markdown says code, benchmarks, and results are public in a footnote,
  but the converted markdown does not include the URL. The reproduction is
  therefore implemented from the paper description.
- A first GENEX attempt only allowed one conditional-monotonicity hop; Gripper
  needs a chain `n_balls_at_a -> m_carried -> at_a`, so chain construction was
  corrected to search multi-step monotonicity paths.

## Deviations from Paper

- The paper uses DLPLAN/TARSKI and SIW/BFWS over standard PDDL benchmark
  suites. This reproduction hand-codes the Gripper transition system, planner,
  and feature pool because the code/data footnote URL is absent from the
  provided markdown. The GENEX and WRAPPER computational steps are preserved.
- The paper's Gripper feature pool has 6,154 features. This reproduction uses a
  smaller generated pool with the relevant Gripper features and distractors so
  the benchmark is fast and reusable in a CPU test job.
- The evaluator adds hard-size and capacity-shift checks beyond the paper's
  Gripper table to make the gym less gameable. These are documented as
  evaluator-derived robustness checks, not paper-reported reference values.
- The optional policy simplification from the paper is implemented for this
  policy representation. It removes redundant rule literals while checking that
  the resulting rule set is still stratified.
