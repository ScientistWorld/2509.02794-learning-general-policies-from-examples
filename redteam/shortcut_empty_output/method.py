"""Shortcut attempt: return an empty constant policy and obtain cheap constraints."""
from redteam.common import empty_policy, write_policy
write_policy(empty_policy())
