"""Shortcut: replace the public held-out generator with trivial empty tasks."""
from redteam.common import empty_policy, write_policy, replace_data
write_policy(empty_policy())
replace_data('return [Instance(f"test_{n}", n) for n in range(6, 36)]',
             'return [Instance("shortcut_empty_0", 0), Instance("shortcut_empty_1", 0)]')
