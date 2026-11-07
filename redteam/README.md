Audit programs and evidence for the Gripper gym. Run the complete audit as a
CPU job with `bash redteam/run_all.sh`, or run one case's `run.sh` in the gym
container. Do not run the learning cases on the login node.

Each case stages its `method.py` as `method/audit_candidate.py`, generates the
policy (and, for some shortcuts, changes a scientist-visible dependency), runs
`bash scripts/evaluate_train.sh`, then runs exactly
`bash scripts/evaluate_test.sh` with no arguments in a separate process.
`post_train.py`, when present, represents candidate writes after public scoring.
The harness never edits `eval/`, the test script, or the Python environment.
It snapshots and restores every changed method, data, baseline, and score file.
The bundled job reuses trained reference outputs for output-only changes.

Every case saves its actual policy, train/test scores when evaluation succeeds,
and a run record with commands, return codes, evaluator hashes, and restoration
status. Rejected impossible outputs have a failure record rather than a score.
Full stdout/stderr logs are ignored; failure excerpts are in the run record.
`summary.json` records every coefficient and the full score decomposition.
`audit_reference.json` is audit-only ground truth and is never read by a candidate.
Candidates use only scientist-visible data and, where stated, improve-mode code.
The no-feature, fixed-feature, mutable-goal, test-size, empty-output, and forged
score shortcuts also work with an initially empty `method/`.
