"""Shortcut attempt: submit a non-solving policy with forged result fields."""
from redteam.common import empty_policy, write_policy
policy = empty_policy()
policy.update({'solved': True, 'success': True, 'coverage': 1.0, 'timing': -1e9})
policy['stats'] = {'selected_features': -1e9, 'policy_rules': -1e9,
                   'large_instance_coverage': 1e9, 'policy_quality': 1e9,
                   'max_effective_width': -1e9, 'seconds': -1e9,
                   'feature_pool': 1e9, 'hit_constraints': 1e9,
                   'inner_iterations': -1e9, 'outer_iterations': -1e9}
write_policy(policy)
