"""Small helpers for candidate programs; these do not read hidden evaluation code."""
from pathlib import Path
import json

ARTIFACT = Path('outputs/genex_gripper/policy.json')


def write_policy(payload):
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')


def reference_policy():
    # The audit reuses a trained output, as permitted. On a new checkout the
    # exact same visible improve-mode learner regenerates it.
    cache = Path('redteam/reference_seed_0/policy.json')
    if cache.exists():
        return json.loads(cache.read_text())
    from method.genex import learn_gripper_policy, policy_to_json
    policy, stats = learn_gripper_policy()
    policy_to_json(policy, stats, ARTIFACT)
    return json.loads(ARTIFACT.read_text())


def empty_policy():
    return {'selected_features': [], 'order': [], 'rules': [], 'stats': {}}


def replace_data(old, new):
    path = Path('data/gripper.py')
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError('Expected exactly one source match for the shortcut')
    path.write_text(text.replace(old, new))
