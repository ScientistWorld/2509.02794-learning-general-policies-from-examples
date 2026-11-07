"""Lightweight checks of saved audit evidence, arithmetic, and restoration.

This does not execute a learner or evaluator. It is safe on the login node.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess

ROOT = Path('/home/user')
HERE = ROOT / 'redteam/audit_v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def main():
    summary = json.loads((HERE / 'summary.json').read_text())
    cases = summary['cases']
    assert len(cases) == 22
    assert summary['reference_matches_supplied']
    assert summary['seed_spread'] == 0
    coefficients = summary['coefficients']
    reference = summary['reference_metrics']
    weight = summary['weight']
    baseline_rows = cases['v2_reference_seed_0']['baselines']
    for name, case in cases.items():
        dest = ROOT / 'redteam' / name
        assert (dest / 'run.sh').exists()
        run = case['run']
        assert run['restored'] and run['evaluator_unchanged']
        assert run['fresh_test_process']
        assert all(s['returncode'] == 0 for s in run['stages'].values())
        assert run['stages']['test']['command'] == ['bash', 'scripts/evaluate_test.sh']
        assert case['baselines'] == baseline_rows
        saved_scores = json.loads((dest / 'scores_test.json').read_text())
        row = saved_scores['experiments']['gripper_generalization']['results'].get('candidate')
        if row is None:
            assert name == 'v2_shortcut_no_artifact'
            assert 'metrics' not in case
            continue
        assert all(math.isfinite(v) for v in row.values())
        independent_delta = weight * sum(coefficients[m] * (row[m] - reference[m]) for m in coefficients)
        assert math.isclose(independent_delta, case['delta'], abs_tol=1e-12)
    assert cases['v2_better_learned_refinement']['delta'] > summary['seed_spread']
    for name in ('v2_weaker_lazy_one_ball', 'v2_weaker_no_pick', 'v2_weaker_redundant_feature'):
        assert cases[name]['delta'] < -summary['seed_spread']
    assert cases['v2_shortcut_handwritten_reference']['metrics'] == reference
    assert cases['v2_shortcut_handwritten_optimal']['metrics'] == cases['v2_better_learned_refinement']['metrics']
    assert cases['v2_shortcut_planner_denominator']['metrics'] == reference
    hashes = [sha(ROOT / f'redteam/v2_reference_seed_{seed}/policy.json') for seed in range(3)]
    assert len(set(hashes)) == 1

    coverage_names = [m for m in coefficients if m.endswith('_coverage')]
    best_failing = -3.95 + sum(coefficients[m] for m in coverage_names)
    assert best_failing < summary['reference_weighted_score']
    baseline_failures = {name: row['delta'] for name, row in baseline_rows.items()}
    assert all(delta < 0 for delta in baseline_failures.values())
    manifest = json.loads((HERE / 'start_manifest.json').read_text())
    mismatches = [name for name, expected in manifest.items() if sha(ROOT / name) != expected]
    assert not mismatches, mismatches
    assert (ROOT / 'scripts/run.sh').read_bytes() == (HERE / 'original_run.sh').read_bytes()
    original_commit = (HERE / 'start_commit.txt').read_text().strip()
    original_run = subprocess.check_output(['git', 'show', original_commit + ':scripts/run.sh'], cwd=ROOT)
    assert (ROOT / 'scripts/run.sh').read_bytes() == original_run
    for run in (c['run'] for c in cases.values()):
        assert all(sha(ROOT / name) == expected for name, expected in run['evaluator_hashes'].items())
    report = (ROOT / 'REDTEAM.md').read_text()
    for name, case in cases.items():
        if case['kind'] == 'shortcut':
            assert f'redteam/{name}/run.sh' in report
    for target in re.findall(r'\]\((redteam/[^)]+)\)', report):
        if target.endswith('verification.json'):
            continue
        assert (ROOT / target).exists(), target
    paying = [name for name, c in cases.items() if c['kind'] == 'shortcut' and c.get('delta', -math.inf) >= 0]
    record = {'all_checks_passed': True, 'job_id': 'ad39d3a8-cc1', 'cases': len(cases),
              'shortcuts': sum(c['kind'] == 'shortcut' for c in cases.values()), 'paying_shortcuts': paying,
              'seed_scores': summary['seed_scores'], 'seed_spread': summary['seed_spread'],
              'seed_policy_sha256': hashes[0], 'reference_matches_supplied': True,
              'maximum_weighted_score_for_any_failing_policy': best_failing,
              'maximum_failing_delta_vs_reference': best_failing - summary['reference_weighted_score'],
              'all_baseline_rows_unchanged': True, 'all_run_returncodes_zero': True,
              'all_run_restorations_passed': True, 'all_evaluator_hashes_unchanged': True,
              'initial_manifest_mismatches': mismatches, 'scripts_run_sh_restored_with_git': True,
              'preexisting_system_deletions': 'Preserved; see initial_status.txt',
              'final_control_file_exception': 'action.yaml must signal done per the job protocol'}
    (HERE / 'verification.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
