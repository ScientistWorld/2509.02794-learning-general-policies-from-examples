# Hardening Report — Gripper generalized-policy gym (paper 2509.02794)

**Verdict.** Better results now score higher. The genuine refinement beats the
reference. Every weaker variant scores below it, including the "lazy" policy,
which the old test ranked *above* the reference. All twelve red-team shortcuts,
plus three new attempts, now fail or have no effect. The reference method
(GENEX + WRAPPER, relearned from the final code) still solves every held-out
instance with 3 features and 4 rules, as the paper reports.

Everything below comes from CPU job `3fc1f5d3-2c7` (exit 0). That job:

- relearned the reference;
- ran every case through `bash scripts/evaluate_test.sh` (no arguments) in a
  fresh process, with only that case's artifact on disk;
- regenerated the score files from the reference alone;
- passed `python validate.py --post-design --compare`.

Per-case artifacts and scores are in `redteam/hardening/cases/`, the summary in
`redteam/hardening/results.json`, and the harness in
`redteam/hardening/harness.py`. "Before" scores come from the verbatim
pre-hardening evaluator (`redteam/hardening/old_gym/`, with the old coefficients
and old reference), or from REDTEAM.md for the shortcuts that edited `data/`.
Rank = Σ coefficient × (candidate − reference), one experiment, weight 1.

## What was wrong, and the fixes

1. **The test followed only the first legal action, on rigged dynamics.**
   `data/gripper.py` forbade every unproductive action: no drop in room A, no
   pick in room B, no moving with empty hands. The evaluator also executed only
   the first admitted successor. So "admit everything" plus the successor order
   solved every instance.
   *Fix:* standard STRIPS Gripper dynamics (move always legal, pick and drop in
   either room). Coverage now uses the paper's definition of solving (§3.1,
   Thm. 1): **every** maximal policy trajectory must be finite and end in a goal
   state. The evaluator explores all admitted successors, so successor order
   no longer matters. The method's WRAPPER test was brought in line with the
   paper (Alg. 2, line 7, "there is a π-trajectory …"); before, it also checked
   only the first-successor path. It still learns the identical policy in one
   outer and one inner iteration.
2. **The paper's constraint was not enforced.** The paper's central claim is
   that learned policies terminate by their structure.
   *Fix:* a validity gate implements Defs. 5 and 8. Every rule must entail a
   feature change, and the features must admit a k-stratified ranking with
   k ≤ 2. An `any` effect counts as a possible increase and decrease, which keeps
   the check sound. The gate also rejects malformed artifacts, unknown feature
   names, features used but not listed as selected, duplicates, and more than 32
   features or 128 rules. Failures are scored as failed runs instead of raising
   an exception.
3. **The evaluator trusted mutable files.** It imported the dynamics, goal
   test, feature definitions, test-instance generator and comparison planner
   from `data/`.
   *Fix:* `eval/train/evaluate_gripper.py` and `eval/test/evaluate_gripper.py`
   are now self-contained, independent copies. Each owns its own dynamics, goal
   test, feature semantics (same names as the `data/` pool; checked equal on 1.4M
   state×feature pairs), BFS optimal plan lengths, instances and baseline
   policies. Neither imports `data/` or `method/`.
4. **Test answers were public.** `data.gripper.test_instances()` generated the
   held-out set.
   *Fix:* the generator was removed. Hidden instances exist only in `eval/test/`.
   Both slices have the same composition with different members:
   - 18 larger instances of mixed parity (up to 60 balls), the larger half
     forming the hard subset;
   - 4 capacity-shift instances (capacity 3–5);
   - 4 initial-state-shift instances (new);
   - the 5 learning instances.
   `evaluate_test.sh` scores every `policy.json` on disk and no longer reads
   `scores_train.json`. No method name is hardcoded: the old
   `genex_gripper → genex_wrapper` mapping was replaced by writing the artifact
   to `outputs/genex_wrapper/`.
5. **A failing method could win on its other metrics.** If a policy is invalid
   or does not solve every instance of the slice, every non-coverage metric is
   pinned to its worst value: quality 0, width 1, plan ratios 3, 20 features,
   40 rules, branching 3. A failing method therefore always ranks strictly below
   any solving one. For solving policies, plan ratios are capped at 3, features
   at 20 and rules at 40.
6. **Self-reported numbers.** The evaluator no longer emits `feature_pool`,
   `inner_iterations`, `outer_iterations` or `hit_constraints`. They stay in
   `reference.json` only as the paper's diagnostics, with coefficient 0.
7. **Baselines were hardcoded numbers.** `baseline_metrics()` returned constants.
   The evaluator now scores three fixed baseline *policies* through the same
   pipeline:
   - `one_step_imitation`: imitates the first plan action;
   - `plan_projection`: the five-ball example plan projected onto the 7 named
     domain features, with no selection or simplification;
   - `admit_all_legal`: invalid under the gate.
   `baseline/` regenerates the first two from `data/` for inspection.

## Metric and weight changes (and why)

- **`policy_quality` (primary) redefined.** Before, it was coverage − 0.05 ×
  mean branching. Now it is IPC-style quality: the mean over large instances of
  optimal plan length ÷ expected trajectory length when an executor picks
  uniformly among the admitted successors. It is 0 unless the policy solves the
  slice. This measures what a nondeterministic general policy actually delivers.
  The value 1.0 in `reference.json` was never paper-reported; it is now labelled
  as the gym's ideal anchor.
- **`max_/avg_plan_length_ratio`** now use the *longest* admitted trajectory
  (worst case) over all held-out instances.
- **Branching coefficients −0.25 / −0.15 → 0** (kept as diagnostics). Under
  the paper's all-trajectories semantics, admitting an extra successor matters
  only through coverage or plan length, and both are scored. A standalone
  branching penalty ranks the wrong way: the lazy policy locks in the worst
  behaviour (one ball per trip), yet scored +0.236 above the reference before.
  The reference also allows the optimal trip.
- **New `initial_state_shift_coverage`** (coefficient 0.3), and
  `max_plan_length_ratio: 1.0` removed from the paper results in
  `reference.json`. The paper does not report plan length, and the old value
  only reflected the first-successor executor.
- **Unchanged:** coverage (1.0 / 0.4 / 0.3 / 0.3), width (−0.3 / −0.2),
  compactness (−0.05 each), plan ratios (−0.1 / −0.05). All paper-reported
  values in `reference.json` are unchanged.

## Do better results score higher?

| Variant | Test result after the fix | Rank before | Rank after |
|---|---|---:|---:|
| Reference (relearned) | solves all; quality 0.9004; worst-case ratio 1.64 / mean 1.377; 3 features / 4 rules | 0 | **0** |
| `better_direct_policy`: leave room A only with a full load or after the last pickup | solves all; quality 1.000; ratio 1.00 / 1.00; 4 / 5 | +0.184 | **+0.0824** |
| `weaker_redundant_feature`: same behaviour, +1 redundant feature | solves all; quality 0.9004; 4 / 4 | −0.050 | **−0.050** |
| `weaker_lazy_one_ball`: carries one ball per trip | solves all; quality 0.754; ratio 1.64 / 1.377 | **+0.236** (wrong direction) | **−0.147** |
| `weaker_no_pick`: pickup rule removed | coverage 0 | −2.566 | **−6.568** |

Noise: relearning with `PYTHONHASHSEED` 0, 1 and 2 gives byte-identical
policies and identical test scores (weighted 2.6175569; spread **0**). The
evaluator is deterministic and every method sees the same instances, so all
comparisons are paired and the +0.0824 margin is exact, not within noise.

## Shortcuts

| Shortcut | Fix that closes it | Rank before | Rank after |
|---|---|---:|---:|
| `shortcut_implicit_planner` (0 features, 1 empty-effect rule) | gate (rule entails no change); all-trajectories semantics | **+0.300** | failed, −6.568 |
| `shortcut_test_answers` (train on the public held-out generator) | generator removed; hidden instances only in `eval/test/` (`from data.gripper import test_instances` → ImportError) | 0 (tie) | cannot run |
| `shortcut_planner_denominator` (planner returns its plan ×100) | optimal lengths by evaluator-owned BFS | **+0.149** | **0.000** (identical to the unmodified reference policy: the edit has no effect) |
| `shortcut_fixed_feature` (redefine `n_balls_at_a` in `data/`) | evaluator-owned feature semantics | **+0.253** | failed, −6.568 |
| `shortcut_mutable_goal` (goal test always true) | evaluator-owned goal test; empty policy is invalid | **+1.234** | failed, −6.568 |
| `shortcut_test_size` (trivial generator in `data/`; rerun on the training generator, the only one left) | evaluator-owned instances | **+0.634** | failed, −6.568 |
| `shortcut_forged_scores` (forged fields and score files) | nothing method-written is read; scores recomputed | −2.266 | failed, −6.568 |
| `shortcut_empty_output` | gate | −2.266 | failed, −6.568 |
| `shortcut_baseline_artifact` (disable baseline modules, corrupt artifact) | baselines owned by the evaluator | −2.266 | failed, −6.568 |
| `shortcut_impossible_values` (null collections) | malformed artifact scored as failed (previously crashed the test) | no score (exception) | failed, −6.568 |
| *new* `shortcut_broad_rules` (3 features, 4 unconditional broad rules) | gate (no 2-stratified ranking) | 0 (tie) | failed, −6.568 |
| *new* `shortcut_undercount_features` (list 2 of the 3 features used) | used features must be selected | **+0.050** | failed, −6.568 |
| *new* `shortcut_unknown_feature` (invented `optimal_distance` feature) | pool owned by the evaluator | no score (exception) | failed, −6.568 |

## Shortcuts left open, and why

- **Hand-writing the policy.** The test scores only the artifact, so a
  hand-written policy, such as the better variant above, is indistinguishable
  from a learned one. `DIRECTION.md` forbids it, and the post-hoc grader must
  check it.
- **Tuning on the visible slice** (`eval/train/` instances). This gives no test
  answers, because the hidden instances differ. `CONSTRAINTS.md` forbids it;
  left to the grader.
- **Reading `eval/test/`.** Out of scope: the test is hidden from scientists.

## Reference score before and after

| | Before | After |
|---|---:|---:|
| `policy_quality` (test) | 0.9415 (old definition) | 0.9004 (new definition) |
| Weighted test score (raw, with each version's coefficients) | 1.7658 | 2.6176 |
| Coverage (large / hard / capacity / train), width | 1 / 1 / 1 / 1, 0 | 1 / 1 / 1 / 1 (+ initial-state 1), 0 |
| Features / rules | 3 / 4 | 3 / 4 |

The raw weighted scores are not comparable across the two coefficient sets.
The reference's rank is 0 by definition in both. On the visible slice the
reference scores 0.8990 quality, versus 0.9004 on the hidden slice, so the two
slices are of comparable difficulty.

Baselines (test, rank vs reference):

- `plan_projection`: 50% large coverage, 60% train coverage, −5.560;
- `one_step_imitation`: 0 coverage, −6.568;
- `admit_all_legal`: invalid, −6.568.

On the visible slice the same three score −5.590, −6.567 and −6.567. The simple
baseline therefore sits clearly below the reference, with room above it.

## Headroom check

- **At the bound:** the reference sits at the bound of `large_instance_coverage`,
  `hard_instance_coverage`, `capacity_shift_coverage`,
  `initial_state_shift_coverage`, `train_coverage` (all 1) and
  `max_/avg_effective_width` (0).
- **Minimal compactness:** its 3 features and 4 rules are the minimum for any
  *valid* (structurally terminating) solving policy over this pool.
  - Moves change only `at_a`/`room_b`.
  - A drop in room B changes neither `n_balls_at_a` nor the room features.
  - A stratified ranking needs a monotone anchor such as `n_balls_at_a`.
  - Each of the 4 action kinds needs its own change-entailing rule.
  - Some 2-feature rule sets do solve every instance semantically, for example
    `{m_carried, at_a}`, but they have no stratified ranking.
- **Room left:**
  - `policy_quality` 0.9004 (bound 1);
  - `max_plan_length_ratio` 1.64 (bound 1);
  - `avg_plan_length_ratio` 1.377 (bound 1).

  This is where the paper's own Gripper policy falls short. Its rule r1
  `{n>0} ↦ {n↓, m?}` together with r3 `{A, m>0} ↦ {¬A}` lets the robot leave
  room A with a single ball while more remain.
- **Attained:** `better_direct_policy` reaches 1.0 / 1.0 / 1.0 and scores
  +0.0824 above the reference after paying for one extra feature and one extra
  rule. The headroom is real and reachable, so no extra experiment was added.

## What I could not fix (stated plainly)

- **The headroom is small and not on the paper's own metric.** The reference
  saturates the paper's metrics (coverage and width). The remaining room is plan
  efficiency, which the paper does not measure, and the best variant gains only
  +0.082. A second domain where the paper's method falls short on coverage (e.g.
  Childsnack at 41.7% in Table 3) would give headroom on the paper's own metric.
  It was not built: it needs a new domain, planner and feature pool, and was out
  of this iteration's budget.
- **The feature pool is fixed** (7 domain features + 120 distractors), so
  research on feature expressivity, which the paper names as its main failure
  cause, cannot show up in this gym. Allowing scientist-defined features would
  reopen the fixed-feature shortcut unless the evaluator interpreted a feature
  grammar itself, as DLPLAN does.
- **The termination gate checks k ≤ 2 only.** A policy that terminates but
  needs k ≥ 3, or one certified only by SIEVE, would be scored as failed, even
  though it is an honest alternative. By design, the gate also rejects rule sets
  that terminate on Gripper but not structurally. The 2-feature
  `{m_carried, at_a}` policy above is one: it solves every instance but would
  otherwise beat the reference on compactness. This enforces the paper's own
  claim; it is not a defect of the test.
- **The state is abstracted over ball and gripper identity**, so successor
  counts and plan lengths are in abstract actions. This is a scaled-down,
  hand-coded Gripper instead of DLPLAN/TARSKI on the IPC files. That
  scale-down was inherited and is unchanged.
