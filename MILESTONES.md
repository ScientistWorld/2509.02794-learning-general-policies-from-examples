# Reproduction Milestones

**Current: core_claim**

## Progress Log

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

## Stop Justification
- Completed at milestone `core_claim`.
