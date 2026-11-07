"""Audit-only ranking; these reference files are never candidate inputs."""
from pathlib import Path
import json

HERE = Path('/home/user/redteam/audit_v2')
EXPERIMENT = 'gripper_generalization'


def main():
    schema = json.loads((HERE / 'reference_coefficients.json').read_text())['experiments']
    supplied = json.loads((HERE / 'reference_scores_test.json').read_text())['experiments']
    ref = supplied[EXPERIMENT]['results']['genex_wrapper']
    metrics = schema[EXPERIMENT]['metrics']
    weight = schema[EXPERIMENT]['weight']
    coefficients = {name: d['coefficient'] for name, d in metrics.items() if d['coefficient']}
    weighted = lambda row: weight * sum(c * row[name] for name, c in coefficients.items())
    summary = {'formula': 'experiment_weight * sum(coefficient * (candidate - reference))',
               'reference_metrics': ref, 'reference_weighted_score': weighted(ref), 'coefficients': coefficients,
               'weight': weight, 'cases': {}}
    for case in json.loads((HERE / 'cases.json').read_text()):
        dest = HERE.parent / case['name']
        run = json.loads((dest / 'run_record.json').read_text())
        result = dict(case, run=run)
        scores = dest / 'scores_test.json'
        if scores.exists() and run['stages'].get('test', {}).get('returncode') == 0:
            rows = json.loads(scores.read_text())['experiments'][EXPERIMENT]['results']
            row = rows.get('candidate')
            if row is not None:
                result.update(metrics=row, weighted_score=weighted(row),
                              delta=sum(weight * c * (row[name] - ref[name]) for name, c in coefficients.items()),
                              contributions={name: weight * c * (row[name] - ref[name]) for name, c in coefficients.items()})
            result['baselines'] = {name: {'metrics': r, 'weighted_score': weighted(r),
                                          'delta': weighted(r)-weighted(ref)}
                                   for name, r in rows.items() if name != 'candidate'}
        summary['cases'][case['name']] = result
        print(case['name'], result.get('delta'), flush=True)
    seeds = [summary['cases']['v2_reference_seed_' + str(i)]['weighted_score'] for i in range(3)]
    summary['seed_scores'] = seeds
    summary['seed_spread'] = max(seeds) - min(seeds)
    summary['reference_matches_supplied'] = summary['cases']['v2_reference_seed_0']['metrics'] == ref
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
