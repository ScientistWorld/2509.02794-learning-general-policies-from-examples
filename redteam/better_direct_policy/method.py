"""Real fix: refine the learned departure rules to require a full or final load."""
from redteam.common import reference_policy, write_policy

policy = reference_policy()
policy['selected_features'].append('space_in_gripper')
policy['selected_features'].sort()
refined = []
for rule in policy['rules']:
    effects = dict(rule['effects'])
    if rule['source_action'] == 'pick':
        effects['space_in_gripper'] = 'down'
    elif rule['source_action'] == 'drop':
        effects['space_in_gripper'] = 'up'
    rule['effects'] = sorted(map(list, effects.items()))
    if rule['source_action'] == 'move_to_b':
        for full_or_final in ['space_in_gripper', 'n_balls_at_a']:
            new_rule = dict(rule)
            new_rule['condition'] = rule['condition'] + [[full_or_final, '0']]
            refined.append(new_rule)
    else:
        refined.append(rule)
policy['rules'] = refined
policy['order'].append(['at_a', 'space_in_gripper'])
policy['stats']['selected_features'] = len(policy['selected_features'])
policy['stats']['policy_rules'] = len(policy['rules'])
write_policy(policy)
