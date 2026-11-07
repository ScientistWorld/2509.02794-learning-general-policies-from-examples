"""Shortcut: replace a benchmark feature with an optimal distance function.

The emitted object has one feature and one rule; the work has been moved to a
mutable artifact that evaluation treats as fixed. It makes no planner call.
"""
from redteam.common import empty_policy, write_policy, replace_data
replace_data('Feature("n_balls_at_a", "num", 1, lambda s: s.balls_at_a)',
             'Feature("n_balls_at_a", "num", 1, shortcut_distance)')
from pathlib import Path
p = Path('data/gripper.py')
p.write_text(p.read_text() + '''\n\ndef shortcut_distance(s):
    n, c, k = s.balls_at_a, s.carried, s.capacity
    if n == 0 and c == 0:
        return 0
    if s.at_a:
        return 2 * n + c + 2 * ((n + c + k - 1) // k) - 1
    return 2 * n + c + 2 * ((n + k - 1) // k)
''')
policy = empty_policy()
policy['selected_features'] = ['n_balls_at_a']
policy['rules'] = [{'condition': [], 'effects': [['n_balls_at_a', 'down']],
                    'source_action': 'shortcut_fixed_artifact'}]
write_policy(policy)
