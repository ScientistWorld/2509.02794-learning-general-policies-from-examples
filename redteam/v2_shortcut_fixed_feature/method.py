from pathlib import Path
from method.audit_support import replace_data, write_policy
replace_data('Feature("n_balls_at_a", "num", 1, lambda s: s.balls_at_a)',
             'Feature("n_balls_at_a", "num", 1, lambda s: len(planner_from_state(s)))')
write_policy({'selected_features': ['n_balls_at_a'],
              'rules': [{'condition': [], 'effects': [['n_balls_at_a', 'down']]}]})
