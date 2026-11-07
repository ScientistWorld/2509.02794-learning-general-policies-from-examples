import os, random
from method.genex import learn_gripper_policy, policy_to_json
from method.audit_support import ARTIFACT
random.seed(int(os.environ['PYTHONHASHSEED']))
policy, stats = learn_gripper_policy()
policy_to_json(policy, stats, ARTIFACT)
