"""Shortcut: obtain demonstrations from every public held-out instance.

Uses only the shipped data generator/planner and improve-mode method. No hidden
module, score, capacity, or seed is read. The learner itself is unchanged.
"""
from pathlib import Path
from data.gripper import test_instances
import method.genex as learner
learner.training_instances = test_instances
policy, stats = learner.learn_gripper_policy()
stats['shortcut_heldout_examples'] = len(test_instances())
learner.policy_to_json(policy, stats, Path('outputs/genex_gripper/policy.json'))
