from method.audit_support import reference_policy, write_policy
policy = reference_policy()
for rule in policy['rules']:
    if rule['source_action'] == 'pick':
        rule['condition'] = [['m_carried', '0']]
write_policy(policy)
