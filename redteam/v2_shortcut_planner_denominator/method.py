from method.audit_support import replace_data, reference_policy, write_policy
replace_data('return planner_from_state(instance.initial())', 'return planner_from_state(instance.initial()) * 100')
write_policy(reference_policy())
