from method.audit_support import reference_policy, write_policy
policy = reference_policy()
policy['selected_features'].append('remaining_work')
for rule in policy['rules']:
    if rule['source_action'] == 'drop':
        rule['effects'].append(['remaining_work', 'down'])
write_policy(policy)
