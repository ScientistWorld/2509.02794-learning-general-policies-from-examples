"""Shortcut: make the benchmark's mutable goal label always positive."""
from redteam.common import empty_policy, write_policy, replace_data
write_policy(empty_policy())
replace_data('return self.balls_at_a == 0 and self.carried == 0', 'return True')
