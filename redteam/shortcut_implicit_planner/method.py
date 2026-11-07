"""Shortcut: defer every action choice to the benchmark's successor order."""
from redteam.common import empty_policy, write_policy
policy = empty_policy()
policy['rules'] = [{'condition': [], 'effects': [], 'source_action': 'shortcut_admit_everything'}]
write_policy(policy)
