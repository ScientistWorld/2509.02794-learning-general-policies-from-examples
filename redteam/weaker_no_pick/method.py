"""Ablation: remove the learned operation required to pick up balls."""
from redteam.common import reference_policy, write_policy
policy = reference_policy()
policy['rules'] = [r for r in policy['rules'] if r['source_action'] != 'pick']
write_policy(policy)
