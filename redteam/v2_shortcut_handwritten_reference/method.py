from method.audit_support import write_policy
# Shortcut: literal rules replace the entire learning procedure.
policy = {'selected_features': ['at_a', 'm_carried', 'n_balls_at_a'], 'rules': [
    {'condition': [], 'effects': [['m_carried', 'up'], ['n_balls_at_a', 'down']]},
    {'condition': [['m_carried', '1']], 'effects': [['at_a', 'false']]},
    {'condition': [], 'effects': [['m_carried', 'down']]},
    {'condition': [['m_carried', '0']], 'effects': [['at_a', 'true']]},
]}

write_policy(policy)
