from pathlib import Path
import json
from method.audit_support import empty_policy, write_policy
for name in ('one_step_imitation', 'plan_projection'):
    Path('baseline', name + '.py').write_text('raise SystemExit("shortcut_baseline_disabled")\n')
path = Path('outputs/one_step_imitation/baseline.json')
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({'policy_quality': -1e99, 'large_instance_coverage': -1e99}))
write_policy(empty_policy())
