# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

## Stop Justification
- Not stopping yet; submitting a rerun on the corrected five-train/thirty-test Gripper split.
