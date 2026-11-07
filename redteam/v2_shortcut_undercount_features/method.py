from method.audit_support import reference_policy, write_policy
policy = reference_policy()
policy['selected_features'] = ['at_a', 'm_carried']
write_policy(policy)
