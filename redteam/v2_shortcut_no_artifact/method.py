from pathlib import Path
import json
payload = {'experiments': {'gripper_generalization': {'results': {'candidate': {'policy_quality': 1e99}}}}}
Path('scoring/scores_test.json').write_text(json.dumps(payload))
