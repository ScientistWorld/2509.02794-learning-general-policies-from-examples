"""Learn rule refinements from planner labels on the five training instances.

Exhaust all states of those small instances. For each additional pool feature,
lift the reference's effects from positive demonstrations, and learn a disjunction
of conjunctions that excludes non-planner transitions. Choose a feasible feature
by rule count, literal count, complexity, then name. No validation/test examples
or hard-coded rule/feature choices are used.
"""
from itertools import product
from data.gripper import all_states, training_instances, feature_pool, planner_from_state, successors, effect, valuation
from method.genex import Rule, _rule_matches


def refine(reference):
    pool = {f.name: f for f in feature_pool(120)}
    examples = []
    for instance in training_instances():
        for state in all_states(instance):
            if not state.is_goal():
                chosen = planner_from_state(state)[0]
                examples.extend((t, t.action == chosen.action) for t in successors(state))
    base_names = reference['selected_features']
    base_features = {name: pool[name] for name in base_names}
    best = None
    diagnostics = []
    for feature in pool.values():
        if feature.name in base_names:
            continue
        names = sorted(base_names + [feature.name])
        features = {name: pool[name] for name in names}
        refined = []
        possible = True
        for raw in reference['rules']:
            base = Rule(tuple(map(tuple, raw['condition'])), tuple(map(tuple, raw['effects'])), raw['source_action'])
            admitted = [(t, label) for t, label in examples if _rule_matches(base, t, base_features)]
            pos = [t for t, label in admitted if label]
            if not pos:
                possible = False
                break
            changes = {effect(feature, t) for t in pos}
            effects = dict(raw['effects'])
            if changes != {'same'}:
                effects[feature.name] = next(iter(changes)) if len(changes) == 1 else 'any'
            lifted = Rule(base.condition, tuple(effects.items()), base.source_action)
            admitted = [(t, label) for t, label in admitted if _rule_matches(lifted, t, features)]
            positive = {tuple(valuation(features[n], t.source) for n in names) for t, label in admitted if label}
            negative = {tuple(valuation(features[n], t.source) for n in names) for t, label in admitted if not label}
            if positive & negative:
                possible = False
                break
            base_condition = dict(base.condition)
            cubes = []
            for values in product((None, '0', '1'), repeat=len(names)):
                condition = dict(base_condition)
                consistent = True
                for n, v in zip(names, values):
                    if v is not None:
                        if n in condition and condition[n] != v:
                            consistent = False
                            break
                        condition[n] = v
                if not consistent:
                    continue
                def matches(row):
                    return all(n not in condition or condition[n] == v for n, v in zip(names, row))
                covered = frozenset(row for row in positive if matches(row))
                if covered and not any(matches(row) for row in negative):
                    cubes.append((covered, tuple(sorted(condition.items()))))
            # Exact cover of the observed positive valuation patterns. There are
            # at most 16 patterns for the four selected features.
            cubes = sorted(set(cubes), key=lambda x: (len(x[1]), x[1]))
            states = {frozenset(): ()}
            for covered, condition in cubes:
                for previous, conditions in list(states.items()):
                    union = previous | covered
                    candidate = conditions + (condition,)
                    score = lambda cs: (len(cs), sum(map(len, cs)), cs)
                    if union not in states or score(candidate) < score(states[union]):
                        states[union] = candidate
            conditions = states.get(frozenset(positive))
            if conditions is None:
                possible = False
                break
            for condition in conditions:
                refined.append({'condition': list(condition), 'effects': sorted(effects.items()),
                                'source_action': base.source_action})
        if possible:
            score = (len(refined), sum(len(r['condition']) for r in refined), feature.complexity, feature.name)
            diagnostics.append({'added_feature': feature.name, 'rules': len(refined)})
            if best is None or score < best[0]:
                best = (score, {'selected_features': names, 'rules': refined})
    if best is None:
        raise RuntimeError('No feature permits exact planner refinement on training states')
    policy = best[1]
    policy['training_evidence'] = {'instances': [i.name for i in training_instances()],
                                   'labelled_transitions': len(examples), 'feasible_candidates': diagnostics}
    return policy
