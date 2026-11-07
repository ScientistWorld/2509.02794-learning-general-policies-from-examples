Current audit of the hardened gym, starting at the commit in `start_commit.txt`.
Earlier `redteam/` results concern earlier gym versions and are not evidence for
this audit. Use only this suite's `v2_*` results and `summary.json`.

Run `bash redteam/audit_v2/run_all.sh` as a CPU job in the gym container, or run
any `redteam/v2_*/run.sh` for one case. Every case deploys its method and helpers,
runs the visible evaluator, and then executes `bash scripts/evaluate_test.sh`
with no arguments in a new process. No background process survives the method.
The evaluator, its imports, and the Python environment are never modified.
The harness restores all source and output bytes after each case.

Each candidate uses only visible data, visible baseline/method code, and (for
output-only changes) the policy relearned in this audit's seed-0 run. The
hand-written shortcuts use none of those trained artifacts. The extra feature
and conditions in `better_learned_refinement` are learned from planner labels on
states of the permitted five training instances, with no validation/test data.

The harness's copies of reference scores and coefficients are audit-only inputs
to ranking. They are not read by candidate programs. Rank uses every nonzero
coefficient and experiment weight, centered on the supplied test reference.
Logs are ignored; score JSONs, policies, return codes, test status, evaluator
hashes, and restoration evidence are retained in each run folder.

The job only temporarily replaces `scripts/run.sh`. Its exact original is
`original_run.sh`; restore it with git when the audit is complete. `action.yaml`
is the system's submit/done control file. Initial preexisting deletions and the
pending action state are recorded in `initial_status.txt`.
