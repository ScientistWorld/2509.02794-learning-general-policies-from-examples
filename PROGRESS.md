# Progress

## What Works

- Implemented the paper's actual core algorithmic pipeline at Gripper scale:
  GENEX hitting-set feature selection, monotonicity chains for stratification,
  projected feature-rule policies, and a WRAPPER-style learner seeded from
  planner transitions.
- `scripts/method.sh` writes `outputs/genex_gripper/policy.json`.
- `scripts/evaluate.sh` independently executes the policy and writes
  `scoring/scores.json`.

## Results

- Local smoke test reproduced the Gripper core claim on the generated benchmark:
  100% training coverage, 100% large-instance coverage, max effective width 0,
  and average effective width 0.
- The learned policy uses 3 selected features, matching the paper's Gripper
  selected-feature count. It has 7 projected rules versus 4 reported in the
  paper because optional policy simplification is not yet implemented.

## Remaining

- Submit the CPU test job to verify the packaged environment.
- Optional next step: implement the paper's policy simplification pass to merge
  projected Gripper rules down toward the reported 4-rule policy.
- Optional next step: add another solved paper domain such as Delivery or Ferry.

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
- Optional policy simplification from the paper is not implemented yet, so the
  projected Gripper policy is correct but less compact than the reported policy.
