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

## Results

- Local smoke test and CPU container job `98e1d2b9-b6a` reproduced the Gripper
  core claim on the generated benchmark: 100% training coverage, 100%
  large-instance coverage, max effective width 0, and average effective width 0.
- The learned policy uses 3 selected features and 4 rules, matching the paper's
  reported Gripper counts. It uses a smaller feature pool than the paper
  because the public code/data URL is missing from the provided markdown.

## Remaining

- Optional next step: add another solved paper domain such as Delivery or Ferry
  to move beyond `core_claim`.

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
- The optional policy simplification from the paper is implemented for this
  policy representation. It removes redundant rule literals while checking that
  the resulting rule set is still stratified.
