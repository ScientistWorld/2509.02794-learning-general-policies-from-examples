from method.audit_support import reference_policy, write_policy
policy = reference_policy()
policy['rules'] = [r for r in policy['rules'] if r['source_action'] != 'pick']
write_policy(policy)
