"""Audit-only aggregation. Candidates never import reference scores or this file."""
from pathlib import Path
import json

ROOT = Path('/home/user')
EXP = 'gripper_generalization'
KEY = 'genex_wrapper'
reference = json.loads((ROOT / 'scoring/reference.json').read_text())
target = json.loads((ROOT / 'scoring/scores_test.json').read_text())
coefficients = {k: v['coefficient'] for k, v in reference['experiments'][EXP]['metrics'].items()}
weight = reference['experiments'][EXP]['weight']
ref = target['experiments'][EXP]['results'][KEY]


def scalar(metrics):
    return weight * sum(c * metrics[k] for k, c in coefficients.items() if c)


def result(metrics):
    return {'weighted_score': scalar(metrics), 'delta_vs_reference': scalar(metrics) - scalar(ref),
            'components_vs_reference': {k: weight * c * (metrics[k] - ref[k])
                                        for k, c in coefficients.items() if c},
            'metrics': metrics}


summary = {'formula': 'sum_experiments(weight * sum_metrics(coefficient * (candidate - reference)))',
           'reference_weighted_score': scalar(ref), 'reference_metrics': ref,
           'coefficients': coefficients, 'experiments_weight': weight, 'cases': {}}
for folder in sorted((ROOT / 'redteam').iterdir()):
    if not folder.is_dir() or not (folder / 'run_record.json').exists():
        continue
    record = json.loads((folder / 'run_record.json').read_text())
    entry = {'stages': record['stages'], 'restored': record['restored'],
             'evaluator_unchanged': record.get('evaluator_unchanged', False)}
    scores = folder / 'scores_test.json'
    if record['stages'].get('test', {}).get('returncode') == 0 and scores.exists():
        payload = json.loads(scores.read_text())['experiments'][EXP]['results']
        if KEY in payload:
            entry.update(result(payload[KEY]))
        if 'one_step_imitation' in payload:
            entry['baseline'] = result(payload['one_step_imitation'])
    summary['cases'][folder.name] = entry

seeds = [summary['cases'][f'reference_seed_{n}']['weighted_score'] for n in range(3)]
summary['seed_scores'] = seeds
summary['seed_spread'] = max(seeds) - min(seeds)
summary['reference_reproduced_exactly'] = all(
    summary['cases'][f'reference_seed_{n}']['metrics'] == ref for n in range(3))
summary['metrics_at_valid_task_bounds'] = {
    'large_instance_coverage': 1.0, 'hard_instance_coverage': 1.0,
    'capacity_shift_coverage': 1.0, 'train_coverage': 1.0,
    'max_effective_width': 0.0, 'avg_effective_width': 0.0,
    'max_plan_length_ratio': 1.0, 'avg_plan_length_ratio': 1.0}
# If every large instance fails under unchanged tasks, hard coverage is zero,
# both widths are one, all plan ratios are zero, policy_quality <= 0, all
# representation/branch penalties <= 0; train/capacity can add at most 0.6.
summary['zero_large_coverage_score_upper_bound'] = 0.3 + 0.3 - 0.3 - 0.2
summary['zero_large_coverage_delta_upper_bound'] = (
    summary['zero_large_coverage_score_upper_bound'] - scalar(ref))
(ROOT / 'redteam/summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
(ROOT / 'redteam/audit_reference.json').write_text(json.dumps(
    {'reference_specification': reference, 'test_target': target}, indent=2, sort_keys=True) + '\n')
for name, entry in summary['cases'].items():
    if 'delta_vs_reference' in entry:
        print(f'{name:38} {entry["weighted_score"]: .9f}  delta {entry["delta_vs_reference"]:+.9f}')
    else:
        print(f'{name:38} NO VALID TEST SCORE')
print(f'Seed spread: {summary["seed_spread"]:.9f}')
