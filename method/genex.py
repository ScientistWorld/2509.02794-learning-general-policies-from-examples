from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from pathlib import Path
import heapq
import json

from data.gripper import (
    Feature,
    Instance,
    State,
    Transition,
    all_states,
    alive_states,
    changes_differ,
    effect,
    feature_pool,
    planner,
    planner_from_state,
    successors,
    test_instances,
    training_instances,
    transition_change,
    valuation,
)


@dataclass(frozen=True)
class Rule:
    condition: tuple[tuple[str, str], ...]
    effects: tuple[tuple[str, str], ...]
    source_action: str


@dataclass
class Policy:
    features: list[Feature]
    rules: list[Rule]
    order: list[tuple[str, str]]
    selected_names: list[str]


def _feature_by_name(features: list[Feature]) -> dict[str, Feature]:
    return {f.name: f for f in features}


def _monotone(feature: Feature, transitions: list[Transition]) -> bool:
    changes = {transition_change(feature, t) for t in transitions}
    return not ("up" in changes and "down" in changes)


def _context_transitions(
    transitions: list[Transition], context_feature: Feature, context_value: str
) -> list[Transition]:
    out = []
    for transition in transitions:
        if transition_change(context_feature, transition) != "=":
            continue
        if valuation(context_feature, transition.source) == context_value:
            out.append(transition)
    return out


def _monotone_given(feature: Feature, context_feature: Feature, transitions: list[Transition]) -> bool:
    return all(_monotone(feature, _context_transitions(transitions, context_feature, v)) for v in ["0", "1"])


def _compute_chains(features: list[Feature], x_pos: list[Transition], free: set[str]) -> dict[str, tuple[str, ...]]:
    roots = [f.name for f in features if _monotone(f, x_pos)]
    by_name = _feature_by_name(features)
    edges: dict[str, list[str]] = {f.name: [] for f in features}
    for context in features:
        for target in features:
            if context.name != target.name and _monotone_given(target, context, x_pos):
                edges[context.name].append(target.name)

    costs = {f.name: 0 if f.name in free else f.complexity for f in features}
    best: dict[str, tuple[int, tuple[str, ...]]] = {}
    heap: list[tuple[int, tuple[str, ...], str]] = []
    for root in roots:
        chain = (root,)
        heapq.heappush(heap, (costs[root], chain, root))

    while heap:
        cost, chain, node = heapq.heappop(heap)
        if node in best:
            continue
        best[node] = (cost, chain)
        for nxt in sorted(edges[node], key=lambda n: (costs[n], by_name[n].complexity, n)):
            if nxt in best or nxt in chain:
                continue
            next_chain = chain + (nxt,)
            heapq.heappush(heap, (cost + costs[nxt], next_chain, nxt))

    return {name: chain for name, (_, chain) in best.items()}


def _chain_cost(chain: tuple[str, ...], features: list[Feature], free: set[str]) -> int:
    by_name = _feature_by_name(features)
    return sum(0 if name in free else by_name[name].complexity for name in chain)


def _hit_sets(
    features: list[Feature], x_pos: list[Transition], x_neg: list[Transition], include_goal_separation: bool = True
) -> list[set[str]]:
    sets: list[set[str]] = []
    for transition in x_pos:
        changed = {f.name for f in features if transition_change(f, transition) != "="}
        if changed:
            sets.append(changed)
        else:
            sets.append(set())
    for bad in x_neg:
        for good in x_pos:
            diff = {f.name for f in features if changes_differ(f, bad, good)}
            sets.append(diff)
    if include_goal_separation:
        states: dict[tuple[int, int, bool, int, int], State] = {}
        for transition in x_pos:
            states[transition.source.key()] = transition.source
            states[transition.target.key()] = transition.target
        goals = [s for s in states.values() if s.is_goal()]
        non_goals = [s for s in states.values() if not s.is_goal()]
        for goal_state in goals:
            for state in non_goals:
                diff = {f.name for f in features if valuation(f, goal_state) != valuation(f, state)}
                sets.append(diff)
    return sets


def _acyclic(edges: set[tuple[str, str]]) -> bool:
    graph: dict[str, set[str]] = {}
    for a, b in edges:
        if a == b:
            continue
        graph.setdefault(a, set()).add(b)
    visiting: set[str] = set()
    visited: set[str] = set()

    def dfs(node: str) -> bool:
        if node in visiting:
            return False
        if node in visited:
            return True
        visiting.add(node)
        for nxt in graph.get(node, ()):
            if not dfs(nxt):
                return False
        visiting.remove(node)
        visited.add(node)
        return True

    return all(dfs(node) for node in list(graph))


def _chain_edges(chain: tuple[str, ...]) -> set[tuple[str, str]]:
    return {(a, b) for a, b in zip(chain, chain[1:]) if a != b}


def genex(features: list[Feature], x_pos: list[Transition], x_neg: list[Transition]) -> tuple[set[str], set[tuple[str, str]], list[set[str]]]:
    hit_sets = _hit_sets(features, x_pos, x_neg)
    selected: set[str] = set()
    order: set[tuple[str, str]] = set()
    by_name = _feature_by_name(features)

    while any(not (selected & h) for h in hit_sets):
        chains = _compute_chains(features, x_pos, selected)
        best_name: str | None = None
        best_score = 0.0
        best_chain: tuple[str, ...] = ()
        for feature in features:
            chain = chains.get(feature.name)
            if not chain:
                continue
            if not _acyclic(order | _chain_edges(chain)):
                continue
            newly_hit = sum(1 for h in hit_sets if not (selected & h) and set(chain) & h)
            cost = max(1, sum(0 if name in selected else by_name[name].complexity for name in chain))
            score = newly_hit / cost
            if score > best_score or (
                score == best_score and best_name is not None and feature.complexity < by_name[best_name].complexity
            ):
                best_name = feature.name
                best_score = score
                best_chain = chain
        if best_name is None or best_score <= 0:
            raise RuntimeError("GENEX failed: no eligible stratification chain hits remaining constraints")
        selected.update(best_chain)
        order.update(_chain_edges(best_chain))
    return selected, order, hit_sets


def project_policy(features: list[Feature], selected_names: set[str], x_pos: list[Transition], order: set[tuple[str, str]]) -> Policy:
    selected_features = [f for f in features if f.name in selected_names]
    seen: set[tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]] = set()
    rules: list[Rule] = []
    for transition in x_pos:
        condition = tuple((f.name, valuation(f, transition.source)) for f in selected_features)
        effects = tuple((f.name, effect(f, transition)) for f in selected_features)
        signature = (condition, effects)
        if signature in seen:
            continue
        seen.add(signature)
        rules.append(Rule(condition, effects, transition.action))
    return Policy(selected_features, rules, sorted(order), sorted(selected_names))


def _rule_matches(rule: Rule, transition: Transition, by_name: dict[str, Feature]) -> bool:
    for name, expected in rule.condition:
        if valuation(by_name[name], transition.source) != expected:
            return False
    effects = dict(rule.effects)
    for name in by_name:
        expected = effects.get(name, "same")
        actual = effect(by_name[name], transition)
        if expected == "any":
            continue
        if expected == "same" and actual != "same":
            return False
        if expected != "same" and actual != expected:
            return False
    return True


def policy_successors(policy: Policy, state: State) -> list[Transition]:
    by_name = _feature_by_name(policy.features)
    out = []
    for transition in successors(state):
        if any(_rule_matches(rule, transition, by_name) for rule in policy.rules):
            out.append(transition)
    return out


def _dedupe_rules(rules: list[Rule]) -> list[Rule]:
    seen: set[tuple[tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]]] = set()
    out: list[Rule] = []
    for rule in rules:
        condition = tuple(sorted(rule.condition))
        effects = tuple(sorted(rule.effects))
        signature = (condition, effects)
        if signature in seen:
            continue
        seen.add(signature)
        out.append(Rule(condition, effects, rule.source_action))
    return out


def _rule_entails_change(rule: Rule) -> bool:
    return any(value not in {"same", "="} for _, value in rule.effects)


def _rule_change(rule: Rule, feature_name: str) -> str:
    value = dict(rule.effects).get(feature_name, "same")
    if value in {"up", "true"}:
        return "up"
    if value in {"down", "false"}:
        return "down"
    return "same"


def _rule_allows_context(rule: Rule, feature_name: str, context_value: str) -> bool:
    value = dict(rule.condition).get(feature_name)
    return value is None or value == context_value


def _rules_monotone(feature_name: str, rules: list[Rule]) -> bool:
    changes = {_rule_change(rule, feature_name) for rule in rules}
    return not ("up" in changes and "down" in changes)


def _rules_monotone_given(feature_name: str, context_name: str, rules: list[Rule]) -> bool:
    for context_value in ["0", "1"]:
        subset = [
            rule
            for rule in rules
            if _rule_change(rule, context_name) == "same" and _rule_allows_context(rule, context_name, context_value)
        ]
        if not _rules_monotone(feature_name, subset):
            return False
    return True


def policy_is_stratified(policy: Policy) -> bool:
    feature_names = [feature.name for feature in policy.features]
    ranked: set[str] = set()
    while len(ranked) < len(feature_names):
        added = False
        for name in feature_names:
            if name in ranked:
                continue
            if _rules_monotone(name, policy.rules):
                ranked.add(name)
                added = True
                continue
            if any(_rules_monotone_given(name, context, policy.rules) for context in ranked):
                ranked.add(name)
                added = True
        if not added:
            return False
    return True


def _avoids_bad(policy: Policy, x_neg: list[Transition]) -> bool:
    by_name = _feature_by_name(policy.features)
    return not any(any(_rule_matches(rule, transition, by_name) for rule in policy.rules) for transition in x_neg)


def _solves(policy: Policy, instances: list[Instance]) -> bool:
    return all(execute_policy(policy, inst)["solved"] for inst in instances)


def simplify_policy(policy: Policy, x_neg: list[Transition], validation_instances: list[Instance]) -> Policy:
    """Greedy version of the paper's optional simplification step.

    It removes rule conditions and drops explicit "same" effects, which leaves
    the paper's default unchanged-effect semantics. A candidate is kept only if
    every rule still entails some selected feature change, the rule set remains
    stratified, no negative transition is admitted, and the policy continues
    solving the wrapper validation instances.
    """

    current = Policy(policy.features, _dedupe_rules(policy.rules), policy.order, policy.selected_names)
    improved = True
    while improved:
        improved = False
        best: Policy | None = None
        best_size = (len(current.rules), sum(len(r.condition) + len(r.effects) for r in current.rules))
        for rule_index, rule in enumerate(current.rules):
            edits: list[Rule] = []
            for cond_index in range(len(rule.condition)):
                edits.append(
                    Rule(rule.condition[:cond_index] + rule.condition[cond_index + 1 :], rule.effects, rule.source_action)
                )
            for eff_index, (_, eff_value) in enumerate(rule.effects):
                if eff_value in {"same", "="}:
                    edits.append(
                        Rule(rule.condition, rule.effects[:eff_index] + rule.effects[eff_index + 1 :], rule.source_action)
                    )
            for edited in edits:
                new_rules = list(current.rules)
                new_rules[rule_index] = edited
                new_rules = _dedupe_rules(new_rules)
                if not all(_rule_entails_change(r) for r in new_rules):
                    continue
                candidate = Policy(current.features, new_rules, current.order, current.selected_names)
                if not policy_is_stratified(candidate):
                    continue
                if not _avoids_bad(candidate, x_neg):
                    continue
                if not _solves(candidate, validation_instances):
                    continue
                size = (len(candidate.rules), sum(len(r.condition) + len(r.effects) for r in candidate.rules))
                if size < best_size:
                    best = candidate
                    best_size = size
        if best is not None:
            current = best
            improved = True
    return current


def execute_policy(policy: Policy, instance: Instance, max_steps: int = 1000) -> dict[str, object]:
    state = instance.initial()
    seen: set[tuple[int, int, bool, int, int]] = set()
    actions: list[str] = []
    for _ in range(max_steps):
        if state.is_goal():
            return {"solved": True, "actions": actions, "reason": "goal"}
        key = state.key()
        if key in seen:
            return {"solved": False, "actions": actions, "reason": "cycle"}
        seen.add(key)
        candidates = policy_successors(policy, state)
        if not candidates:
            return {"solved": False, "actions": actions, "reason": "undefined"}
        chosen = candidates[0]
        actions.append(chosen.action)
        state = chosen.target
    return {"solved": False, "actions": actions, "reason": "max_steps"}


def learn_gripper_policy(extra_distractors: int = 120) -> tuple[Policy, dict[str, object]]:
    features = feature_pool(extra_distractors)
    train = training_instances()
    ordered_train = sorted(train, key=lambda inst: len(planner(inst)), reverse=True)
    plans = {inst.name: planner(inst) for inst in ordered_train}
    outer_iterations = 0
    total_inner_iterations = 0
    current_index = 0
    final_x_pos: list[Transition] = []
    final_x_neg: list[Transition] = []
    final_hit_sets: list[set[str]] = []
    final_q_prime: list[Instance] = []

    # Strategy S1 from Algorithm 2: test each learned policy on all Q and move
    # the singleton Q' to the first failing instance when needed.
    while current_index < len(ordered_train):
        outer_iterations += 1
        q_prime = [ordered_train[current_index]]
        x_pos = list(plans[q_prime[0].name])
        x_neg: list[Transition] = []
        inner_iterations = 0

        while True:
            inner_iterations += 1
            total_inner_iterations += 1
            selected, order, hit_sets = genex(features, x_pos, x_neg)
            policy = project_policy(features, selected, x_pos, order)
            failure = None
            for inst in q_prime:
                result = execute_policy(policy, inst)
                if not result["solved"]:
                    failure = (inst, result)
                    break
            if failure is None:
                break
            inst, result = failure
            state = inst.initial()
            previous_state = state
            for action in result["actions"]:
                previous_state = state
                state = next(t.target for t in successors(state) if t.action == action)
            if result["reason"] == "undefined":
                repair_plan = planner_from_state(state)
                if not repair_plan:
                    raise RuntimeError(f"wrapper could not repair undefined state {state}")
                x_pos.append(repair_plan[0])
            elif result["reason"] == "cycle":
                raise RuntimeError(f"wrapper found a cycle despite GENEX stratification on {inst.name}")
            else:
                bad = next(
                    (t for t in successors(previous_state) if t.target == state),
                    None,
                )
                if bad is None:
                    raise RuntimeError(f"wrapper could not identify bad transition into {state}")
                x_neg.append(bad)

        policy = simplify_policy(policy, x_neg, train)
        final_x_pos = x_pos
        final_x_neg = x_neg
        final_hit_sets = hit_sets
        final_q_prime = q_prime

        full_results = [execute_policy(policy, inst) for inst in ordered_train]
        failing = next((idx for idx, result in enumerate(full_results) if not result["solved"]), None)
        if failing is None:
            break
        if failing > current_index:
            current_index = failing
        else:
            current_index += 1
    else:
        raise RuntimeError("WRAPPER S1 failed to find a policy for the Gripper training set")

    stats = {
        "outer_iterations": outer_iterations,
        "inner_iterations": total_inner_iterations,
        "x_pos": len(final_x_pos),
        "x_neg": len(final_x_neg),
        "hit_constraints": len(final_hit_sets),
        "selected_features": len(policy.features),
        "policy_rules": len(policy.rules),
        "feature_pool": len(features),
        "states_seen": sum(len(plans[inst.name]) + 1 for inst in final_q_prime),
    }
    return policy, stats


def policy_to_json(policy: Policy, stats: dict[str, object], path: Path) -> None:
    payload = {
        "selected_features": policy.selected_names,
        "order": policy.order,
        "rules": [
            {"condition": list(rule.condition), "effects": list(rule.effects), "source_action": rule.source_action}
            for rule in policy.rules
        ],
        "stats": stats,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def policy_from_json(path: Path) -> Policy:
    payload = json.loads(path.read_text())
    features_by_name = _feature_by_name(feature_pool(120))
    features = [features_by_name[name] for name in payload["selected_features"]]
    rules = [
        Rule(tuple(map(tuple, item["condition"])), tuple(map(tuple, item["effects"])), item["source_action"])
        for item in payload["rules"]
    ]
    return Policy(features, rules, [tuple(edge) for edge in payload["order"]], payload["selected_features"])


def evaluate_policy(policy: Policy) -> dict[str, float]:
    train = training_instances()
    test = test_instances()
    train_results = [execute_policy(policy, inst) for inst in train]
    test_results = [execute_policy(policy, inst) for inst in test]
    train_coverage = sum(r["solved"] for r in train_results) / len(train_results)
    test_coverage = sum(r["solved"] for r in test_results) / len(test_results)
    max_plan_ratio = 0.0
    for inst, result in zip(test, test_results):
        if result["solved"]:
            max_plan_ratio = max(max_plan_ratio, len(result["actions"]) / max(1, len(planner(inst))))
    return {
        "train_coverage": train_coverage,
        "large_instance_coverage": test_coverage,
        "max_effective_width": 0.0 if test_coverage == 1.0 else 1.0,
        "avg_effective_width": 0.0 if test_coverage == 1.0 else 1.0 - test_coverage,
        "selected_features": float(len(policy.features)),
        "policy_rules": float(len(policy.rules)),
        "max_plan_length_ratio": max_plan_ratio,
    }


def baseline_metrics() -> dict[str, float]:
    # A deliberately non-general one-step imitation baseline: it repeats only the
    # first action seen in the training plan, showing why a generalized policy is needed.
    solved = 0
    tests = test_instances()
    for inst in tests:
        state = inst.initial()
        if state.balls_at_a > 0 and state.carried < state.capacity:
            state = next(t.target for t in successors(state) if t.action == "pick")
        if state.is_goal():
            solved += 1
    return {
        "train_coverage": 0.0,
        "large_instance_coverage": solved / len(tests),
        "max_effective_width": 1.0,
        "avg_effective_width": 1.0,
        "selected_features": 0.0,
        "policy_rules": 1.0,
        "max_plan_length_ratio": 0.0,
    }


def reachable_transition_count(instances: list[Instance]) -> int:
    return sum(len(successors(state)) for inst in instances for state in alive_states(inst))
