"""Run a single candidate, public eval, then the unchanged no-argument test.

Candidate execution and evaluation are separate processes; no background process,
test-source mutation, interpreter mutation, or evaluator import hook is used.
Only the two-file policy interface is carried from candidate to evaluation.
The candidate may also change the ordinary visible source/artifact files tested
by its shortcut. Everything outside redteam is restored, even on failure.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = Path('/home/user')
HERE = ROOT / 'redteam/audit_v2'
ROOTS = ('outputs', 'checkpoints', 'method_outputs')
WATCHED = ['data/gripper.py', 'baseline/one_step_imitation.py', 'baseline/plan_projection.py',
           'scoring/scores.json', 'scoring/scores_train.json', 'scoring/scores_test.json',
           'method/audit_candidate.py', 'method/audit_support.py', 'method/audit_refine.py',
           'method/audit_reference_policy.json', 'outputs/candidate/policy.json',
           'outputs/one_step_imitation/baseline.json']


def artifacts():
    return [p for root in ROOTS if Path(root).exists() for p in Path(root).rglob('policy.json') if p.is_file()]


def snapshot():
    paths = set(WATCHED) | {str(p) for p in artifacts()}
    return {n: (Path(n).read_bytes(), Path(n).stat().st_mode & 0o777) if Path(n).exists() else None for n in paths}


def restore(saved):
    for p in artifacts():
        if str(p) not in saved:
            p.unlink()
    for n, v in saved.items():
        p = Path(n)
        if v is None:
            p.unlink(missing_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(v[0])
            p.chmod(v[1])
    for root in ('method', 'data', 'baseline'):
        shutil.rmtree(Path(root) / '__pycache__', ignore_errors=True)
    for folder in ['outputs/candidate', 'outputs/one_step_imitation']:
        p = Path(folder)
        if p.exists() and not any(p.iterdir()):
            p.rmdir()


def protected_hashes():
    paths = list(Path('eval').rglob('*.py')) + [Path('scripts/evaluate_test.sh')]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def run(case):
    os.chdir(ROOT)
    dest = ROOT / 'redteam' / case
    seed = int(case.rsplit('_', 1)[-1]) if case.startswith('v2_reference_seed_') else 0
    saved = snapshot()
    protected = protected_hashes()
    record = {'case': case, 'seed': seed, 'test_command': 'bash scripts/evaluate_test.sh',
              'fresh_test_process': True, 'candidate_inputs': 'visible sources plus trained improve-mode policy only',
              'evaluator_hashes': protected, 'stages': {}}
    started = time.monotonic()
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    try:
        for p in artifacts():
            p.unlink()
        shutil.copyfile(dest / 'method.py', 'method/audit_candidate.py')
        shutil.copyfile(HERE / 'support.py', 'method/audit_support.py')
        shutil.copyfile(HERE / 'refine.py', 'method/audit_refine.py')
        reference = ROOT / 'redteam/v2_reference_seed_0/policy.json'
        if reference.exists():
            shutil.copyfile(reference, 'method/audit_reference_policy.json')
        stages = [('method', [sys.executable, '-m', 'method.audit_candidate']),
                  ('train', ['bash', 'scripts/evaluate_train.sh'])]
        if (dest / 'post_train.py').exists():
            stages.append(('post_train', [sys.executable, str(dest / 'post_train.py')]))
        stages.append(('test', ['bash', 'scripts/evaluate_test.sh']))
        for stage, command in stages:
            with (dest / (stage + '.log')).open('w') as log:
                result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=1200)
            record['stages'][stage] = {'command': command, 'returncode': result.returncode}
            if stage in ('train', 'test') and result.returncode == 0:
                shutil.copyfile('scoring/scores_' + stage + '.json', dest / ('scores_' + stage + '.json'))
            if result.returncode:
                record['stages'][stage]['error_tail'] = (dest / (stage + '.log')).read_text()[-4000:]
            if stage == 'method' and result.returncode:
                raise RuntimeError('candidate execution failed')
        if Path('outputs/candidate/policy.json').exists():
            shutil.copyfile('outputs/candidate/policy.json', dest / 'policy.json')
        if Path('data/gripper.py').read_bytes() != saved['data/gripper.py'][0]:
            shutil.copyfile('data/gripper.py', dest / 'deployed_gripper.py')
        test_lines = (dest / 'test.log').read_text().splitlines()
        record['test_status'] = next((line for line in test_lines if line.startswith('[test] candidate')), None)
        assert protected_hashes() == protected, 'evaluator changed'
        record['evaluator_unchanged'] = True
    except Exception as error:
        record['error'] = repr(error)
    finally:
        restore(saved)
        record['restored'] = all(not Path(n).exists() if v is None else Path(n).read_bytes() == v[0]
                                 for n, v in saved.items())
        record['seconds'] = time.monotonic() - started
        (dest / 'run_record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: record.get(k) for k in ('case', 'test_status', 'restored', 'error', 'seconds')}), flush=True)
    if record.get('error') or not record['restored']:
        raise SystemExit(1)


if __name__ == '__main__':
    run(sys.argv[1])
