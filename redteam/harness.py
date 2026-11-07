"""Deploy a candidate, run the public script and the restored hidden script.

Each script runs in a new process with the standard environment. No evaluator,
Python installation, or process is modified. All transient source/output changes
are restored, including on failure; only redteam evidence persists.
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
os.chdir(ROOT)
CASE = sys.argv[1]
DEST = ROOT / 'redteam' / CASE
SEED = CASE.rsplit('_', 1)[-1] if CASE.startswith('reference_seed_') else '0'


def snapshot():
    paths = [Path('data/gripper.py'), Path('baseline/one_step_imitation.py'),
             Path('outputs/one_step_imitation/baseline.json'),
             Path('scoring/scores.json'), Path('scoring/scores_train.json'),
             Path('scoring/scores_test.json'), Path('method/audit_candidate.py')]
    for folder in ['outputs', 'checkpoints', 'method_outputs']:
        root = Path(folder)
        if root.exists():
            paths.extend(root.glob('**/policy.json'))
    paths.append(Path('outputs/genex_gripper/policy.json'))
    return {str(p): (p.read_bytes(), p.stat().st_mode & 0o777) if p.exists() else None
            for p in set(paths)}


def restore(saved):
    for folder in ['outputs', 'checkpoints', 'method_outputs']:
        root = Path(folder)
        if root.exists():
            for p in root.glob('**/policy.json'):
                if str(p) not in saved:
                    p.unlink()
    for name, value in saved.items():
        p = Path(name)
        if value is None:
            p.unlink(missing_ok=True)
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(value[0])
            p.chmod(value[1])
    # Avoid stale bytecode after short-lived data-source edits.
    for folder in ['data/__pycache__', 'method/__pycache__', 'baseline/__pycache__']:
        shutil.rmtree(folder, ignore_errors=True)


def evaluator_hashes():
    paths = list(Path('eval').rglob('*.py')) + [Path('scripts/evaluate_test.sh')]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


saved = snapshot()
protected = evaluator_hashes()
env = dict(os.environ, PYTHONHASHSEED=SEED)
record = {'case': CASE, 'seed': int(SEED), 'test_command': 'bash scripts/evaluate_test.sh',
          'fresh_test_process': True, 'stages': {}, 'evaluator_hashes': protected}
started = time.monotonic()
try:
    # Keep only the candidate policy discoverable. Baseline is evaluator-owned.
    for folder in ['outputs', 'checkpoints', 'method_outputs']:
        p = Path(folder)
        if p.exists():
            for artifact in p.glob('**/policy.json'):
                artifact.unlink()
    shutil.copyfile(DEST / 'method.py', 'method/audit_candidate.py')
    stages = [('method', [sys.executable, '-m', 'method.audit_candidate'])]
    stages += [('train', ['bash', 'scripts/evaluate_train.sh'])]
    post = DEST / 'post_train.py'
    if post.exists():
        stages.append(('post_train', [sys.executable, '-m', f'redteam.{CASE}.post_train']))
    stages.append(('test', ['bash', 'scripts/evaluate_test.sh']))
    for name, command in stages:
        if name == 'test':
            # Keep candidate-written files in place exactly as in deployment.
            out = Path('scoring/scores_test.json')
            if out.exists():
                shutil.copyfile(out, DEST / 'preexisting_test_scores.json')
        with (DEST / f'{name}.log').open('w') as log:
            run = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 timeout=1200)
        record['stages'][name] = {'returncode': run.returncode, 'command': command}
        if name in ('train', 'test'):
            scores = Path(f'scoring/scores_{name}.json')
            if scores.exists() and run.returncode == 0:
                shutil.copyfile(scores, DEST / f'scores_{name}.json')
        if name == 'post_train':
            shutil.copyfile('scoring/scores_train.json', DEST / 'submitted_train_scores.json')
        if run.returncode != 0:
            # Invalid public outputs are still tested in an independent process.
            record['stages'][name]['error_tail'] = (DEST / f'{name}.log').read_text()[-3500:]
            if name == 'method':
                break
    artifact = Path('outputs/genex_gripper/policy.json')
    if artifact.exists():
        shutil.copyfile(artifact, DEST / 'policy.json')
    if Path('data/gripper.py').read_bytes() != saved['data/gripper.py'][0]:
        shutil.copyfile('data/gripper.py', DEST / 'deployed_gripper.py')
    assert evaluator_hashes() == protected, 'Protected evaluation source changed'
    record['evaluator_unchanged'] = True
except Exception as error:
    record['error'] = repr(error)
finally:
    restore(saved)
    record['restored'] = all((not Path(p).exists() if v is None else Path(p).read_bytes() == v[0])
                             for p, v in saved.items())
    record['seconds'] = time.monotonic() - started
    (DEST / 'run_record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
print(json.dumps({'case': CASE, 'stages': record['stages'], 'seconds': record['seconds'],
                  'restored': record['restored']}, sort_keys=True), flush=True)
if record.get('error') or not record['restored']:
    raise SystemExit(1)
