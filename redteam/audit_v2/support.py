"""Candidate helpers. Deployed as method/audit_support.py; no hidden imports."""
from pathlib import Path
import json

ARTIFACT = Path('outputs/candidate/policy.json')
CACHE = Path('method/audit_reference_policy.json')


def write_policy(policy):
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(policy, indent=2, sort_keys=True) + '\n')


def reference_policy():
    # This is a trained improve-mode artifact staged by the audit, never a
    # hidden answer or a policy copied from an earlier audit.
    return json.loads(CACHE.read_text())


def empty_policy():
    return {'selected_features': [], 'rules': []}


def replace_data(old, new):
    path = Path('data/gripper.py')
    source = path.read_text()
    assert source.count(old) == 1, old
    path.write_text(source.replace(old, new))
