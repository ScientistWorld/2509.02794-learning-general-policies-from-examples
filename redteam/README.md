The current audit is documented in [../REDTEAM.md](../REDTEAM.md). Its code and
reference arithmetic are in `audit_v2/`, and the 22 actual experiment folders
are named `v2_*`. Run `bash redteam/audit_v2/run_all.sh` as a CPU job in the gym
container. Each `v2_*/run.sh` also runs one case independently, restores its
temporary changes, and retains scores and a run record in its own folder.

The current audit uses the unchanged no-argument hidden test in a separate
process. Candidate code reads only scientist-visible resources, and output-only
cases reuse this audit's relearned reference. No evaluator or Python environment
mutation is used. Audit-only reference score files are never candidate inputs.

All other folders preserve historical audits and hardening checks of earlier
gym versions. Their scores and the old `run_all.sh` are historical evidence,
not results for this iteration. Use `audit_v2/summary.json` for current ranks.
Logs, caches, and temporary state are ignored; sources, small policies, score
files, and run records are committed.
