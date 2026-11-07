"""Materialize independent, reviewable candidate programs (no evaluation run)."""
from pathlib import Path
import json

ROOT = Path('/home/user')
HERE = ROOT / 'redteam/audit_v2'
CASES = []

def add(name, kind, description, source, post=None):
    name = 'v2_' + name
    folder = ROOT / 'redteam' / name
    folder.mkdir(exist_ok=True)
    (folder / 'method.py').write_text(source.strip() + '\n')
    (folder / 'run.sh').write_text('#!/bin/bash\nset -euo pipefail\ncd /home/user\npython -m redteam.audit_v2.harness ' + name + '\n')
    (folder / 'run.sh').chmod(0o755)
    if post is not None:
        (folder / 'post_train.py').write_text(post.strip() + '\n')
    CASES.append({'name': name, 'kind': kind, 'description': description})

for seed in range(3):
    add('reference_seed_' + str(seed), 'reference', 'Full GENEX + WRAPPER relearning with Python and hash seed ' + str(seed), '''
import os, random
from method.genex import learn_gripper_policy, policy_to_json
from method.audit_support import ARTIFACT
random.seed(int(os.environ['PYTHONHASHSEED']))
policy, stats = learn_gripper_policy()
policy_to_json(policy, stats, ARTIFACT)
''')

add('better_learned_refinement', 'better', 'Learn extra feature and minimal rule conditions from planner-labelled states of the five training instances', '''
from method.audit_support import reference_policy, write_policy
from method.audit_refine import refine
write_policy(refine(reference_policy()))
''')
add('weaker_no_pick', 'weaker', 'Ablate the learned pickup rule', '''
from method.audit_support import reference_policy, write_policy
policy = reference_policy()
policy['rules'] = [r for r in policy['rules'] if r['source_action'] != 'pick']
write_policy(policy)
''')
add('weaker_lazy_one_ball', 'weaker', 'Restrict pickup to empty grippers: one ball per trip', '''
from method.audit_support import reference_policy, write_policy
policy = reference_policy()
for rule in policy['rules']:
    if rule['source_action'] == 'pick':
        rule['condition'] = [['m_carried', '0']]
write_policy(policy)
''')
add('weaker_redundant_feature', 'weaker', 'Same trajectories with a redundant fourth selected feature', '''
from method.audit_support import reference_policy, write_policy
policy = reference_policy()
policy['selected_features'].append('remaining_work')
for rule in policy['rules']:
    if rule['source_action'] == 'drop':
        rule['effects'].append(['remaining_work', 'down'])
write_policy(policy)
''')

# Both hand-written shortcuts can run in from-scratch mode: they import no
# learner and inspect no reference artifact, evaluation source, or data labels.
manual_reference = '''
from method.audit_support import write_policy
# Shortcut: literal rules replace the entire learning procedure.
policy = {'selected_features': ['at_a', 'm_carried', 'n_balls_at_a'], 'rules': [
    {'condition': [], 'effects': [['m_carried', 'up'], ['n_balls_at_a', 'down']]},
    {'condition': [['m_carried', '1']], 'effects': [['at_a', 'false']]},
    {'condition': [], 'effects': [['m_carried', 'down']]},
    {'condition': [['m_carried', '0']], 'effects': [['at_a', 'true']]},
]}
'''
add('shortcut_handwritten_reference', 'shortcut', 'Hand-write four rules without any learning: reference-behaviour shortcut', manual_reference + '\nwrite_policy(policy)')
add('shortcut_handwritten_optimal', 'shortcut', 'Hand-write full/final-load departure logic without any learning', '''
from method.audit_support import write_policy
# Shortcut: the answer is a literal policy; no demonstrations are consumed.
write_policy({'selected_features': ['at_a', 'm_carried', 'n_balls_at_a', 'space_in_gripper'], 'rules': [
    {'condition': [], 'effects': [['m_carried', 'up'], ['n_balls_at_a', 'down'], ['space_in_gripper', 'down']]},
    {'condition': [['m_carried', '1'], ['space_in_gripper', '0']], 'effects': [['at_a', 'false']]},
    {'condition': [['m_carried', '1'], ['n_balls_at_a', '0']], 'effects': [['at_a', 'false']]},
    {'condition': [], 'effects': [['m_carried', 'down'], ['space_in_gripper', 'up']]},
    {'condition': [['m_carried', '0']], 'effects': [['at_a', 'true']]},
]})
''')
add('shortcut_forged_scores', 'shortcut', 'Empty policy plus forged scores, flags, timings, and metrics after public evaluation', '''
from method.audit_support import empty_policy, write_policy
policy = empty_policy()
policy.update(success=True, solved=True, elapsed_seconds=-1e99, policy_quality=1e99,
              selected_feature_count=-1e99, policy_rule_count=-1e99,
              stats={'feature_pool': 1e99, 'selected_features': -1e99, 'policy_rules': -1e99})
write_policy(policy)
''', post='''
from pathlib import Path
import json
metrics = {name: 1e99 for name in ('policy_quality', 'large_instance_coverage', 'hard_instance_coverage',
           'capacity_shift_coverage', 'initial_state_shift_coverage', 'train_coverage')}
metrics.update({name: -1e99 for name in ('selected_features', 'policy_rules', 'max_effective_width',
               'avg_effective_width', 'max_plan_length_ratio', 'avg_plan_length_ratio')})
payload = {'slice': 'test', 'experiments': {'gripper_generalization': {'results': {'candidate': metrics}}}}
for name in ('scores.json', 'scores_train.json', 'scores_test.json'):
    Path('scoring', name).write_text(json.dumps(payload))
''')
add('shortcut_implicit_planner', 'shortcut', 'Admit every successor with zero features and one empty-effect rule', '''
from method.audit_support import write_policy
write_policy({'selected_features': [], 'rules': [{'condition': [], 'effects': []}]})
''')
add('shortcut_empty_output', 'shortcut', 'Empty constant artifact: zero features and zero rules', '''
from method.audit_support import empty_policy, write_policy
write_policy(empty_policy())
''')
add('shortcut_impossible_values', 'shortcut', 'Null feature/rule lists plus NaN quality and negative-infinite timings', '''
from method.audit_support import write_policy
write_policy({'selected_features': None, 'rules': None, 'policy_quality': float('nan'),
              'success': True, 'elapsed_seconds': float('-inf')})
''')
add('shortcut_undercount_features', 'shortcut', 'Keep reference effects but omit the monotone anchor from selected_features', '''
from method.audit_support import reference_policy, write_policy
policy = reference_policy()
policy['selected_features'] = ['at_a', 'm_carried']
write_policy(policy)
''')
add('shortcut_fixed_feature', 'shortcut', 'Replace data-side n_balls_at_a by planner distance; emit a one-feature one-rule policy', '''
from pathlib import Path
from method.audit_support import replace_data, write_policy
replace_data('Feature("n_balls_at_a", "num", 1, lambda s: s.balls_at_a)',
             'Feature("n_balls_at_a", "num", 1, lambda s: len(planner_from_state(s)))')
write_policy({'selected_features': ['n_balls_at_a'],
              'rules': [{'condition': [], 'effects': [['n_balls_at_a', 'down']]}]})
''')
add('shortcut_unknown_feature', 'shortcut', 'Invent an optimal-distance feature name and always descend it', '''
from method.audit_support import write_policy
write_policy({'selected_features': ['optimal_distance'],
              'rules': [{'condition': [], 'effects': [['optimal_distance', 'down']]}]})
''')
add('shortcut_mutable_goal_and_size', 'shortcut', 'Trivialize data-side goals and generators; submit an empty policy', '''
from method.audit_support import replace_data, empty_policy, write_policy
replace_data('return self.balls_at_a == 0 and self.carried == 0', 'return True')
replace_data('return [Instance(f"train_{n}", n) for n in range(1, 6)]', 'return [Instance("shortcut_zero", 0)]')
write_policy(empty_policy())
''')
add('shortcut_planner_denominator', 'shortcut', 'Multiply planner length by 100 while reusing reference policy: tie shortcut', '''
from method.audit_support import replace_data, reference_policy, write_policy
replace_data('return planner_from_state(instance.initial())', 'return planner_from_state(instance.initial()) * 100')
write_policy(reference_policy())
''')
add('shortcut_baseline_artifact', 'shortcut', 'Disable and corrupt both visible baselines; submit an empty policy', '''
from pathlib import Path
import json
from method.audit_support import empty_policy, write_policy
for name in ('one_step_imitation', 'plan_projection'):
    Path('baseline', name + '.py').write_text('raise SystemExit("shortcut_baseline_disabled")\\n')
path = Path('outputs/one_step_imitation/baseline.json')
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps({'policy_quality': -1e99, 'large_instance_coverage': -1e99}))
write_policy(empty_policy())
''')
add('shortcut_test_answers', 'shortcut', 'Attempt to obtain held-out demonstrations from the visible data generator; empty fallback if absent', '''
from method.audit_support import empty_policy, write_policy
try:
    from data.gripper import test_instances
except ImportError as error:
    print('shortcut_test_answers unavailable:', error)
    write_policy(empty_policy())
else:
    from pathlib import Path
    import method.genex as learner
    from method.audit_support import ARTIFACT
    learner.training_instances = test_instances
    policy, stats = learner.learn_gripper_policy()
    learner.policy_to_json(policy, stats, ARTIFACT)
''')
add('shortcut_copied_baseline', 'shortcut', 'Copy the visible plan-projection artifact without running a learner', '''
from baseline.plan_projection import build_policy
from method.audit_support import write_policy
write_policy(build_policy())
''')
add('shortcut_no_artifact', 'shortcut', 'Emit no policy and try to retain a candidate-written perfect score file', '''
from pathlib import Path
import json
payload = {'experiments': {'gripper_generalization': {'results': {'candidate': {'policy_quality': 1e99}}}}}
Path('scoring/scores_test.json').write_text(json.dumps(payload))
''')

(HERE / 'cases.json').write_text(json.dumps(CASES, indent=2) + '\n')
(HERE / 'run_all.sh').write_text('#!/bin/bash\nset -euo pipefail\ncd /home/user\n' +
                               ''.join('bash redteam/' + c['name'] + '/run.sh\n' for c in CASES) +
                               'python -m redteam.audit_v2.summarize\n')
(HERE / 'run_all.sh').chmod(0o755)
print('Wrote', len(CASES), 'cases')
