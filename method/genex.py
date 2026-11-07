from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from pathlib import Path
import heapq
import json

from types import ModuleType
from typing import Any

from data import gripper as gripper_domain
from data.policy_features import (
    Feature,
    Transition,
    changes_differ,
    effect,
    transition_change,
    valuation,
)

# A domain module (data/gripper.py, data/childsnack.py) provides: successors,
# planner, planner_from_state, feature_pool, training_instances, and optionally
# is_dead_end. States provide is_goal() and key(); instances provide initial().
Domain = ModuleType
State = Any
Instance = Any


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


def _monotonicity_graph(
    features: list[Feature], x_pos: list[Transition]
) -> tuple[list[str], dict[str, list[str]]]:
    """Monotone roots and edges g -> f ("f is monotone in X+ given g").

    Same definitions as `_monotone` and `_monotone_given`, evaluated with
    per-feature bitmasks over the transitions of X+ for speed.
    """
    up: dict[str, int] = {}
    down: dict[str, int] = {}
    same: dict[str, int] = {}
    positive: dict[str, int] = {}
    for f in features:
        u = d = e = pos = 0
        for index, transition in enumerate(x_pos):
            bit = 1 << index
            change = transition_change(f, transition)
            if change == "up":
                u |= bit
            elif change == "down":
                d |= bit
            else:
                e |= bit
            if valuation(f, transition.source) == "1":
                pos |= bit
        up[f.name], down[f.name], same[f.name], positive[f.name] = u, d, e, pos
    everything = (1 << len(x_pos)) - 1

    def monotone(name: str, mask: int) -> bool:
        return not (up[name] & mask and down[name] & mask)

    roots = [f.name for f in features if monotone(f.name, everything)]
    edges: dict[str, list[str]] = {f.name: [] for f in features}
    for context in features:
        c = context.name
        contexts = (same[c] & ~positive[c] & everything, same[c] & positive[c])
        for target in features:
            t = target.name
            if t != c and all(monotone(t, mask) for mask in contexts):
                edges[c].append(t)
    return roots, edges


def _compute_chains(
    features: list[Feature],
    x_pos: list[Transition],
    free: set[str],
    graph: tuple[list[str], dict[str, list[str]]] | None = None,
) -> dict[str, tuple[str, ...]]:
    roots, edges = graph if graph is not None else _monotonicity_graph(features, x_pos)
    by_name = _feature_by_name(features)

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
        states: dict[tuple, State] = {}
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

    graph = _monotonicity_graph(features, x_pos)
    while any(not (selected & h) for h in hit_sets):
        chains = _compute_chains(features, x_pos, selected, graph)
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


def policy_successors(policy: Policy, state: State, domain: Domain = gripper_domain) -> list[Transition]:
    by_name = _feature_by_name(policy.features)
    out = []
    for transition in domain.successors(state):
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
    if value == "any":
        return "any"
    return "same"


def _rule_allows_context(rule: Rule, feature_name: str, context_value: str) -> bool:
    value = dict(rule.condition).get(feature_name)
    return value is None or value == context_value


def _rules_monotone(feature_name: str, rules: list[Rule]) -> bool:
    changes = {_rule_change(rule, feature_name) for rule in rules}
    if "any" in changes:
        changes |= {"up", "down"}
    return not ("up" in changes and "down" in changes)


def _rules_monotone_given(feature_name: str, context_name: str, rules: list[Rule]) -> bool:
    for context_value in ["0", "1"]:
        subset = [
            rule
            for rule in rules
            if _rule_change(rule, context_name) in {"same", "any"}
            and _rule_allows_context(rule, context_name, context_value)
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


def _solves(policy: Policy, instances: list[Instance], domain: Domain = gripper_domain) -> bool:
    return all(verify_policy(policy, inst, domain)["solved"] for inst in instances)


def _keeps_monotonicities(policy: Policy) -> bool:
    """The chain monotonicities that GENEX established still hold on the rules.

    For every ordering pair (g, f) in Ord, f stays monotone given g, and every
    feature with no predecessor in Ord stays monotone. This keeps the policy
    stratified under the same ranking (Sec. 7, optional simplification).
    """
    names = [feature.name for feature in policy.features]
    predecessors: dict[str, list[str]] = {name: [] for name in names}
    for g, f in policy.order:
        if f in predecessors and g in predecessors:
            predecessors[f].append(g)
    for name in names:
        if _rules_monotone(name, policy.rules):
            continue
        if not predecessors[name]:
            return False
        if not all(_rules_monotone_given(name, g, policy.rules) for g in predecessors[name]):
            return False
    return True


def simplify_policy(
    policy: Policy,
    x_neg: list[Transition],
    q_prime: list[Instance] | None = None,
    domain: Domain = gripper_domain,
) -> Policy:
    """Optional simplification step of WRAPPER (Alg. 2, line 6).

    Iteratively attempts to remove a rule condition (the paper's "simplify only
    conditions" configuration), merging rules that become identical, or to drop
    an explicit "same" effect (the default meaning, so semantics are
    unchanged); the first edit that keeps the invariant is applied, until no
    edit applies. The invariant: every rule entails a feature change,
    the policy keeps the same conditional monotonicities (hence stays
    stratified under the same ranking), and no bad transition in X- becomes a
    policy transition, and the policy still solves the instances of Q' it was
    tested on (when given).
    """

    current = Policy(policy.features, _dedupe_rules(policy.rules), policy.order, policy.selected_names)
    improved = True
    while improved:
        improved = False
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
                if not _keeps_monotonicities(candidate) or not policy_is_stratified(candidate):
                    continue
                if not _avoids_bad(candidate, x_neg):
                    continue
                if q_prime is not None and not _solves(candidate, q_prime, domain):
                    continue
                current = candidate
                improved = True
                break
            if improved:
                break
    return current


def _is_dead_end(state: State, domain: Domain = gripper_domain) -> bool:
    if hasattr(domain, "is_dead_end"):
        return domain.is_dead_end(state)
    try:
        domain.planner_from_state(state)
    except RuntimeError:
        return True
    return False


def verify_policy(policy: Policy, instance: Instance, domain: Domain = gripper_domain) -> dict[str, object]:
    """WRAPPER test (Alg. 2, line 7): explore every policy trajectory.

    Returns the first alive state where the policy is undefined (not closed),
    the first policy transition into a dead end (not safe), or a cycle. A
    policy solves the instance iff all maximal trajectories reach the goal.
    """
    start = instance.initial()
    states: dict[tuple, State] = {start.key(): start}
    graph: dict[tuple, list[tuple]] = {}
    frontier = deque([start])
    while frontier:
        state = frontier.popleft()
        if state.is_goal():
            graph[state.key()] = []
            continue
        candidates = policy_successors(policy, state, domain)
        if not candidates:
            return {"solved": False, "reason": "undefined", "state": state}
        graph[state.key()] = []
        for transition in candidates:
            target = transition.target
            if not target.is_goal() and _is_dead_end(target, domain):
                return {"solved": False, "reason": "dead_end", "transition": transition}
            graph[state.key()].append(target.key())
            if target.key() not in states:
                states[target.key()] = target
                frontier.append(target)
    indegree = {key: 0 for key in graph}
    for succ in graph.values():
        for key in succ:
            indegree[key] += 1
    order = [key for key, degree in indegree.items() if degree == 0]
    for key in order:
        for nxt in graph[key]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                order.append(nxt)
    if len(order) != len(graph):
        return {"solved": False, "reason": "cycle"}
    return {"solved": True, "reason": "goal", "states": len(graph)}


class WrapperFailure(RuntimeError):
    pass


def _union(groups: list[list[Transition]]) -> list[Transition]:
    out: list[Transition] = []
    seen: set[tuple] = set()
    for group in groups:
        for transition in group:
            key = (transition.source.key(), transition.target.key())
            if key not in seen:
                seen.add(key)
                out.append(transition)
    return out


def _inner_loop(
    domain: Domain,
    features: list[Feature],
    q_prime: list[Instance],
    x_pos_by: dict[str, list[Transition]],
    x_neg_by: dict[str, list[Transition]],
) -> tuple[Policy, list[Transition], list[Transition], list[set[str]], int]:
    """Alg. 2, lines 3-7: GENEX on X+/X- of Q', simplify, test on Q', repeat.

    X+_P and X-_P are kept per instance P, so augmentations persist when P is
    part of a later Q'.
    """
    inner_iterations = 0
    while True:
        inner_iterations += 1
        x_pos = _union([x_pos_by[inst.name] for inst in q_prime])
        x_neg = _union([x_neg_by[inst.name] for inst in q_prime])
        try:
            selected, order, hit_sets = genex(features, x_pos, x_neg)
        except RuntimeError as error:
            raise WrapperFailure(str(error)) from error
        policy = project_policy(features, selected, x_pos, order)
        if all(verify_policy(policy, inst, domain)["solved"] for inst in q_prime):
            policy = simplify_policy(policy, x_neg, q_prime, domain)
        failure = None
        for inst in q_prime:
            result = verify_policy(policy, inst, domain)
            if not result["solved"]:
                failure = (inst, result)
                break
        if failure is None:
            return policy, x_pos, x_neg, hit_sets, inner_iterations
        inst, result = failure
        if result["reason"] == "undefined":
            # Not closed: add a planner-recommended transition from the state.
            repair_plan = domain.planner_from_state(result["state"])
            if not repair_plan:
                raise WrapperFailure(f"wrapper could not repair undefined state {result['state']}")
            x_pos_by[inst.name].append(repair_plan[0])
        elif result["reason"] == "dead_end":
            # Not safe: the last policy transition into the dead end is bad.
            x_neg_by[inst.name].append(result["transition"])
        else:
            raise WrapperFailure(f"wrapper found a cycle despite GENEX stratification on {inst.name}")


def _wrapper(
    domain: Domain, features: list[Feature], ordered_train: list[Instance], plans: dict, strategy: str
) -> tuple[Policy, dict[str, object]]:
    """Alg. 2 outer loop with strategy S1 (singleton Q') or S2 (growing Q')."""
    x_pos_by = {inst.name: list(plans[inst.name]) for inst in ordered_train}
    x_neg_by: dict[str, list[Transition]] = {inst.name: [] for inst in ordered_train}
    q_indices = [0]
    outer_iterations = 0
    total_inner_iterations = 0
    max_outer = len(ordered_train) if strategy == "S1" else len(ordered_train) ** 2
    while outer_iterations < max_outer:
        outer_iterations += 1
        q_prime = [ordered_train[i] for i in q_indices]
        policy, x_pos, x_neg, hit_sets, inner = _inner_loop(domain, features, q_prime, x_pos_by, x_neg_by)
        total_inner_iterations += inner

        full_results = [verify_policy(policy, inst, domain) for inst in ordered_train]
        failing = next((idx for idx, result in enumerate(full_results) if not result["solved"]), None)
        if failing is None:
            stats = {
                "strategy": strategy,
                "outer_iterations": outer_iterations,
                "inner_iterations": total_inner_iterations,
                "last_q_prime": len(q_prime),
                "last_inner_iterations": inner,
                "x_pos": len(x_pos),
                "x_neg": len(x_neg),
                "hit_constraints": len(hit_sets),
                "selected_features": len(policy.features),
                "policy_rules": len(policy.rules),
                "feature_pool": len(features),
                "states_seen": sum(len(plans[inst.name]) + 1 for inst in q_prime),
            }
            return policy, stats
        k = max(q_indices)
        if strategy == "S1":
            if failing > k:
                q_indices = [failing]
            elif k + 1 < len(ordered_train):
                q_indices = [k + 1]
            else:
                break
        else:
            q_indices = sorted(set(q_indices) | {failing}) if failing < k else [failing]
    raise WrapperFailure(f"WRAPPER {strategy} found no policy that solves the training set")


def learn_policy(domain: Domain, extra_distractors: int = 120) -> tuple[Policy, dict[str, object]]:
    """GENEX + WRAPPER (Algorithms 1 and 2) on a domain's training set.

    As in the paper's experiments, WRAPPER starts with strategy S1 and
    switches to strategy S2 when S1 fails.
    """
    features = domain.feature_pool(extra_distractors)
    train = domain.training_instances()
    plans = {inst.name: domain.planner(inst) for inst in train}
    # Static ordering P1, P2, ... by plan length, larger to shorter (stable).
    ordered_train = sorted(train, key=lambda inst: len(plans[inst.name]), reverse=True)
    try:
        return _wrapper(domain, features, ordered_train, plans, "S1")
    except WrapperFailure:
        return _wrapper(domain, features, ordered_train, plans, "S2")


def learn_gripper_policy(extra_distractors: int = 120) -> tuple[Policy, dict[str, object]]:
    return learn_policy(gripper_domain, extra_distractors)


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


def policy_from_json(path: Path, domain: Domain = gripper_domain) -> Policy:
    payload = json.loads(path.read_text())
    features_by_name = _feature_by_name(domain.feature_pool(120))
    features = [features_by_name[name] for name in payload["selected_features"]]
    rules = [
        Rule(tuple(map(tuple, item["condition"])), tuple(map(tuple, item["effects"])), item["source_action"])
        for item in payload["rules"]
    ]
    return Policy(features, rules, [tuple(edge) for edge in payload["order"]], payload["selected_features"])


def reachable_transition_count(instances: list[Instance], domain: Domain = gripper_domain) -> int:
    return sum(
        len(domain.successors(state)) for inst in instances for state in domain.all_states(inst) if not state.is_goal()
    )
