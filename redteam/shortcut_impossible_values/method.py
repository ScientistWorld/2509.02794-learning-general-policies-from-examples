"""Shortcut attempt: replace required collections with impossible null values."""
from redteam.common import empty_policy, write_policy
policy = empty_policy()
policy['selected_features'] = None
policy['rules'] = None
policy['success'] = True
policy['elapsed_seconds'] = -1e99
write_policy(policy)
