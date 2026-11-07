from method.genex import learn_gripper_policy, policy_to_json
from pathlib import Path
import os
import random
random.seed(int(os.environ.get('PYTHONHASHSEED', '0')))
policy, stats = learn_gripper_policy()
policy_to_json(policy, stats, Path('outputs/genex_gripper/policy.json'))
