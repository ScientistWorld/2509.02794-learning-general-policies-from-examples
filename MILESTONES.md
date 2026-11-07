# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-31 07:13] - core_claim
- Implemented GENEX hitting-set feature selection with monotonicity chains and a WRAPPER-style repair loop for Gripper.
- Completed CPU container job `98e1d2b9-b6a`, which regenerated the policy, evaluated it independently, and passed `python validate.py --compare`.
- Reproduced the Gripper core claim with 100% training coverage, 100% larger-instance coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:17] - core_claim
- Continuing-agent audit found the implementation is a real scaled-down GENEX/WRAPPER reproduction, not a surrogate.
- Re-ran `scripts/reproduce.sh`, standalone `scripts/evaluate.sh`, and `python validate.py --compare`; all passed locally.
- Verified the one-step imitation baseline fails on held-out Gripper instances while GENEX reaches 100% held-out coverage, supporting the core generalization claim.

### [2026-05-31 07:18] - core_claim
- Completed CPU container job `86843c23-d46` on the corrected five-training/thirty-held-out Gripper split.
- The job regenerated `outputs/genex_gripper/policy.json`, wrote `scoring/scores.json`, and passed `python validate.py --compare`.
- Reconfirmed the core claim with 100% train coverage, 100% held-out coverage, effective width 0, 3 selected features, and 4 policy rules.

### [2026-05-31 07:35] - core_claim
- Verified the paper's released code repository URL from the recovered footnote: `https://github.com/bonetblai/learner-policies-from-examples`.
- Updated the default evaluator so `scoring/scores.json` includes the same benefit and constraint metrics defined in `scoring/reference.json`.
- Local rerun of `scripts/method.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` passed.

### [2026-05-31 07:45] - core_claim
- Final verification kept the milestone at `core_claim`.
- Tightened method-agnostic wording in evaluation and direction documentation for from-scratch gym use.
- Documented which reference metrics are paper-reported versus gym-derived, then re-ran `scripts/evaluate.sh` and `python validate.py --compare` successfully.

### [2026-05-31 07:49] - core_claim
- Added a tracked one-step imitation baseline implementation and made default evaluation report both GENEX and baseline scores.
- Aligned `TARGETS.md`, `CONSTRAINTS.md`, and `DIRECTION.md` with the hard-instance, capacity-shift, and branching metrics that are actually scored.
- Local `scripts/reproduce.sh`, `scripts/evaluate_train.sh`, `scripts/evaluate_test.sh`, and `python validate.py --compare` all passed; submitting a CPU job for container verification.

### [2026-05-31 07:52] - core_claim
- Completed final verification without downgrading the milestone.
- Confirmed method/problem separation, download portability, train/test evaluator wiring, and scoring coefficients are suitable for the Gripper gym.
- Fixed a stale baseline-script comment and removed generated Python cache folders, then re-ran `python validate.py --compare` successfully.

### [2026-11-07] - core_claim (hardening)
- Gym hardened against the red-team report. Changes:
  - standard Gripper dynamics, scored with the paper's all-trajectories notion of solving;
  - a structural-termination gate (k-stratified, k <= 2);
  - evaluator-owned dynamics, features, optimal lengths, instances and baselines;
  - hidden test instances that exist only in `eval/test/`;
  - failure pinning.
- WRAPPER verification now explores every policy trajectory (Alg. 2, line 7).
  It still learns the paper's 3-feature / 4-rule Gripper policy in 1 outer and 1 inner iteration.
- CPU job `3fc1f5d3-2c7`:
  - the reference solves every hidden instance;
  - genuine refinement +0.082, lazy variant -0.147;
  - all shortcuts fail or have no effect;
  - seed spread 0.
  See `HARDENING.md`.

## Stop Justification
- Completed at milestone `core_claim`.
