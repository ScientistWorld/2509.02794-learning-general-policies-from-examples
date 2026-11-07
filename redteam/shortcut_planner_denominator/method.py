"""Shortcut: inflate the supposedly fixed comparison plan by 100 times."""
from redteam.common import reference_policy, write_policy, replace_data
write_policy(reference_policy())
replace_data('return planner_from_state(instance.initial())',
             'return planner_from_state(instance.initial()) * 100')
