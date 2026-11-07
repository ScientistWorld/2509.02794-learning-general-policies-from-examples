"""Visible train-slice evaluator for the Gripper generalized-policy gym.

Self-contained by design: this module owns the dynamics, the goal test, the
semantics of every named feature, optimal plan lengths, the instances, and the
baseline policies. It imports nothing from `data/`, `method/`, or `eval/test/`,
so a submission cannot change what it is compared against.

A policy artifact is a JSON object with `selected_features` (names from the
feature pool) and `rules` (each with `condition` and `effects`). Every other
field in the artifact is ignored; every scored number is recomputed here.

Semantics (Bonet & Geffner, "Learning General Policies From Examples"):
- A transition (s, t) is a policy transition if it is compatible with a rule.
- A policy solves an instance iff every maximal policy trajectory from the
  initial state is finite and ends in a goal state (closed, safe, acyclic).
  All admitted successors are explored; no tie-breaking order is used.
- The rule set must be structurally terminating: every rule entails a feature
  change and the features admit a k-stratified ranking (k <= 2). A policy that
  fails this check, or is malformed, scores as failed on every metric.
- If the policy does not solve every instance of the slice, all non-coverage
  metrics are pinned to their worst values, so a failing policy never outranks
  a solving one through compactness or efficiency.
"""
from __future__ import annotations

from collections import deque
from itertools import combinations, product

EXPERIMENT = "gripper_generalization"

# ---------------------------------------------------------------------------
# Instances: (name, balls, capacity, balls_at_a, carried, robot_at_a)
# ---------------------------------------------------------------------------


def _standard(name: str, balls: int, capacity: int = 2) -> tuple:
    return (name, balls, capacity, balls, 0, True)


TRAIN_INSTANCES = [_standard(f"learn_{n}", n) for n in range(1, 6)]
LARGE_INSTANCES = [
    _standard(f"large_{n}", n)
    for n in [6, 9, 10, 13, 14, 17, 18, 21, 22, 25, 26, 29, 30, 33, 34, 41, 47, 56]
]
CAPACITY_INSTANCES = [
    _standard("capacity_3_balls_8", 8, 3),
    _standard("capacity_3_balls_14", 14, 3),
    _standard("capacity_4_balls_20", 20, 4),
    _standard("capacity_5_balls_27", 27, 5),
]
INITIAL_STATE_INSTANCES = [
    ("init_12_robot_b_mixed", 12, 2, 7, 1, False),
    ("init_16_robot_b_all_a", 16, 2, 16, 0, False),
    ("init_19_cap3_holding", 19, 3, 10, 2, True),
    ("init_25_cap2_only_held", 25, 2, 0, 2, True),
]

# Pinned values for failed or invalid runs (worst value of each metric).
WORST_SUCCESSORS = 3.0  # pick, drop, move: the most legal actions at any state
PLAN_RATIO_CAP = 3.0
FEATURE_CAP = 20.0
RULE_CAP = 40.0
MAX_SELECTED_FEATURES = 32
MAX_RULES = 128
STRATIFICATION_K = 2

# ---------------------------------------------------------------------------
# Dynamics. State = (balls_at_a, carried, robot_at_a, total, capacity)
# ---------------------------------------------------------------------------


def _initial(spec: tuple) -> tuple:
    _, balls, capacity, at_a, carried, robot_at_a = spec
    return (at_a, carried, robot_at_a, balls, capacity)


def _is_goal(state: tuple) -> bool:
    return state[0] == 0 and state[1] == 0


def _successors(state: tuple) -> list[tuple]:
    at_a, carried, robot_at_a, total, capacity = state
    at_b = total - at_a - carried
    out = []
    here = at_a if robot_at_a else at_b
    if here > 0 and carried < capacity:
        out.append((at_a - 1 if robot_at_a else at_a, carried + 1, robot_at_a, total, capacity))
    if carried > 0:
        out.append((at_a + 1 if robot_at_a else at_a, carried - 1, robot_at_a, total, capacity))
    out.append((at_a, carried, not robot_at_a, total, capacity))
    return out


def _optimal_length(start: tuple) -> int:
    if _is_goal(start):
        return 0
    frontier = deque([start])
    depth = {start: 0}
    while frontier:
        state = frontier.popleft()
        for nxt in _successors(state):
            if nxt in depth:
                continue
            depth[nxt] = depth[state] + 1
            if _is_goal(nxt):
                return depth[nxt]
            frontier.append(nxt)
    raise RuntimeError(f"unsolvable instance from {start}")


# ---------------------------------------------------------------------------
# Feature pool: name -> (kind, function of state)
# ---------------------------------------------------------------------------


def _build_pool() -> dict:
    pool = {
        "n_balls_at_a": ("num", lambda s: s[0]),
        "m_carried": ("num", lambda s: s[1]),
        "at_a": ("bool", lambda s: s[2]),
        "goal": ("bool", lambda s: s[0] == 0 and s[1] == 0),
        "room_b": ("bool", lambda s: not s[2]),
        "space_in_gripper": ("num", lambda s: s[4] - s[1]),
        "remaining_work": ("num", lambda s: s[0] + s[1]),
    }
    for i in range(120):
        mod = 2 + (i % 7)
        offset = i // 7
        pool[f"distractor_{i:03d}"] = (
            "num",
            lambda s, mod=mod, offset=offset: (s[3] * (offset + 1) + s[0]) % mod,
        )
    return pool


POOL = _build_pool()
EFFECTS = {"num": {"up", "down", "same", "any"}, "bool": {"true", "false", "same", "any"}}
CHANGE_EFFECTS = {"up", "down", "true", "false"}

# ---------------------------------------------------------------------------
# Policy parsing and structural checks
# ---------------------------------------------------------------------------


class InvalidPolicy(Exception):
    pass


def _parse_condition_value(value) -> str:
    if isinstance(value, bool):
        raise InvalidPolicy("condition values must be '0' or '1'")
    if isinstance(value, int) and value in (0, 1):
        return str(value)
    if isinstance(value, str) and value in ("0", "1"):
        return value
    raise InvalidPolicy(f"condition value {value!r} is not '0' or '1'")


def _parse_pairs(items, selected: set, what: str, rule_index: int) -> list:
    if not isinstance(items, list):
        raise InvalidPolicy(f"rule {rule_index}: {what} must be a list")
    pairs = []
    seen = set()
    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) != 2 or not isinstance(item[0], str):
            raise InvalidPolicy(f"rule {rule_index}: malformed {what} entry {item!r}")
        name = item[0]
        if name not in selected:
            raise InvalidPolicy(f"rule {rule_index}: {what} uses unselected feature {name!r}")
        if name in seen:
            raise InvalidPolicy(f"rule {rule_index}: feature {name!r} repeated in {what}")
        seen.add(name)
        pairs.append((name, item[1]))
    return pairs


def parse_policy(payload, pool: dict | None = None) -> tuple[list[str], list[tuple[dict, dict]]]:
    pool = POOL if pool is None else pool
    if not isinstance(payload, dict):
        raise InvalidPolicy("policy artifact must be a JSON object")
    features = payload.get("selected_features")
    rules = payload.get("rules")
    if not isinstance(features, list) or not all(isinstance(name, str) for name in features):
        raise InvalidPolicy("selected_features must be a list of feature names")
    if len(set(features)) != len(features):
        raise InvalidPolicy("selected_features contains duplicates")
    if len(features) > MAX_SELECTED_FEATURES:
        raise InvalidPolicy(f"more than {MAX_SELECTED_FEATURES} selected features")
    unknown = [name for name in features if name not in pool]
    if unknown:
        raise InvalidPolicy(f"unknown feature names: {unknown[:5]}")
    if not isinstance(rules, list) or not rules:
        raise InvalidPolicy("rules must be a non-empty list")
    if len(rules) > MAX_RULES:
        raise InvalidPolicy(f"more than {MAX_RULES} rules")
    selected = set(features)
    parsed = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            raise InvalidPolicy(f"rule {index} must be an object")
        condition = {
            name: _parse_condition_value(value)
            for name, value in _parse_pairs(rule.get("condition"), selected, "condition", index)
        }
        effects = {}
        for name, value in _parse_pairs(rule.get("effects"), selected, "effects", index):
            kind = pool[name][0]
            if not isinstance(value, str) or value not in EFFECTS[kind]:
                raise InvalidPolicy(f"rule {index}: effect {value!r} invalid for {kind} feature {name!r}")
            effects[name] = value
        parsed.append((condition, effects))
    return list(features), parsed


def _directions(value: str | None) -> set:
    if value in ("up", "true"):
        return {"up"}
    if value in ("down", "false"):
        return {"down"}
    if value == "any":
        return {"up", "down"}
    return set()


def structural_termination(features: list[str], rules: list[tuple[dict, dict]], k: int = STRATIFICATION_K) -> str | None:
    """Return None if the rule set is k-stratified (Defs. 5 and 8), else a reason.

    `any` effects count as possible increases and decreases for monotonicity,
    and as possibly-unchanged for the conditioning contexts.
    """
    for index, (_, effects) in enumerate(rules):
        if not any(value in CHANGE_EFFECTS for value in effects.values()):
            return f"rule {index} entails no feature change"
    up, down, keeps, allow0, allow1 = {}, {}, {}, {}, {}
    for f in features:
        up[f] = down[f] = keeps[f] = allow0[f] = allow1[f] = 0
        for index, (condition, effects) in enumerate(rules):
            bit = 1 << index
            dirs = _directions(effects.get(f))
            if "up" in dirs:
                up[f] |= bit
            if "down" in dirs:
                down[f] |= bit
            if effects.get(f) in (None, "same", "any"):
                keeps[f] |= bit
            if condition.get(f) != "1":
                allow0[f] |= bit
            if condition.get(f) != "0":
                allow1[f] |= bit
    everything = (1 << len(rules)) - 1

    def monotone(f: str, mask: int) -> bool:
        return not (up[f] & mask and down[f] & mask)

    ranked = [f for f in features if monotone(f, everything)]
    pending = [f for f in features if f not in ranked]
    progress = True
    while pending and progress:
        progress = False
        for f in list(pending):
            done = False
            for size in range(1, k + 1):
                for group in combinations(ranked, size):
                    ok = True
                    for values in product((0, 1), repeat=size):
                        mask = everything
                        for g, v in zip(group, values):
                            mask &= keeps[g] & (allow1[g] if v else allow0[g])
                        if not monotone(f, mask):
                            ok = False
                            break
                    if ok:
                        done = True
                        break
                if done:
                    break
            if done:
                ranked.append(f)
                pending.remove(f)
                progress = True
    if pending:
        return f"no {k}-stratified ranking for features {pending[:5]}"
    return None


# ---------------------------------------------------------------------------
# Policy execution over all policy trajectories
# ---------------------------------------------------------------------------


class CompiledPolicy:
    def __init__(self, features: list[str], rules: list[tuple[dict, dict]], pool: dict | None = None):
        pool = POOL if pool is None else pool
        self.features = features
        self.kinds = [pool[f][0] for f in features]
        self.functions = [pool[f][1] for f in features]
        index = {f: i for i, f in enumerate(features)}
        self.rules = [
            (
                [(index[f], v) for f, v in condition.items()],
                [effects.get(f, "same") for f in features],
            )
            for condition, effects in rules
        ]
        self._cache: dict = {}

    def _values(self, state: tuple) -> tuple:
        values = self._cache.get(state)
        if values is None:
            values = tuple(fn(state) for fn in self.functions)
            self._cache[state] = values
        return values

    def admits(self, source: tuple, target: tuple) -> bool:
        before = self._values(source)
        after = self._values(target)
        changes = []
        for kind, b, a in zip(self.kinds, before, after):
            if kind == "bool":
                changes.append("same" if bool(b) == bool(a) else ("true" if a else "false"))
            else:
                changes.append("up" if a > b else ("down" if a < b else "same"))
        positive = [("1" if (bool(b) if kind == "bool" else b > 0) else "0") for kind, b in zip(self.kinds, before)]
        for condition, effects in self.rules:
            if any(positive[i] != v for i, v in condition):
                continue
            if all(e == "any" or e == c for e, c in zip(effects, changes)):
                return True
        return False


def analyze_instance(policy: CompiledPolicy, spec: tuple) -> dict:
    start = _initial(spec)
    graph: dict = {}
    frontier = deque([start])
    seen = {start}
    undefined = 0
    alive = 0
    branching = []
    while frontier:
        state = frontier.popleft()
        if _is_goal(state):
            graph[state] = []
            continue
        alive += 1
        admitted = [t for t in _successors(state) if policy.admits(state, t)]
        graph[state] = admitted
        branching.append(len(admitted))
        if not admitted:
            undefined += 1
        for nxt in admitted:
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    # Kahn's algorithm on the reachable policy graph detects cycles.
    indegree = {s: 0 for s in graph}
    for s, succ in graph.items():
        for t in succ:
            indegree[t] += 1
    order = [s for s, d in indegree.items() if d == 0]
    cursor = 0
    while cursor < len(order):
        s = order[cursor]
        cursor += 1
        for t in graph[s]:
            indegree[t] -= 1
            if indegree[t] == 0:
                order.append(t)
    acyclic = len(order) == len(graph)
    solved = acyclic and undefined == 0
    result = {
        "solved": solved,
        "reason": "solved" if solved else ("cycle" if not acyclic else "undefined"),
        "undefined_fraction": undefined / alive if alive else 0.0,
        "branching": branching,
    }
    if solved:
        worst: dict = {}
        expected: dict = {}
        for s in reversed(order):
            succ = graph[s]
            if not succ:
                worst[s] = 0
                expected[s] = 0.0
            else:
                worst[s] = 1 + max(worst[t] for t in succ)
                expected[s] = 1.0 + sum(expected[t] for t in succ) / len(succ)
        optimal = _optimal_length(start)
        result.update(
            {
                "optimal": optimal,
                "worst_ratio": worst[start] / optimal if optimal else 1.0,
                "expected_ratio": expected[start] / optimal if optimal else 1.0,
            }
        )
    return result


def _hard(instances: list[tuple]) -> list[tuple]:
    threshold = sorted(spec[1] for spec in instances)[len(instances) // 2]
    return [spec for spec in instances if spec[1] >= threshold]


def _failed_metrics(coverages: dict) -> dict:
    metrics = {
        "policy_quality": 0.0,
        "max_effective_width": 1.0,
        "avg_effective_width": 1.0,
        "max_applicable_successors": WORST_SUCCESSORS,
        "avg_applicable_successors": WORST_SUCCESSORS,
        "selected_features": FEATURE_CAP,
        "policy_rules": RULE_CAP,
        "max_plan_length_ratio": PLAN_RATIO_CAP,
        "avg_plan_length_ratio": PLAN_RATIO_CAP,
    }
    metrics.update(coverages)
    return metrics


def evaluate_payload(payload) -> tuple[dict, str]:
    zero = {
        "train_coverage": 0.0,
        "large_instance_coverage": 0.0,
        "hard_instance_coverage": 0.0,
        "capacity_shift_coverage": 0.0,
        "initial_state_shift_coverage": 0.0,
    }
    try:
        features, rules = parse_policy(payload)
        reason = structural_termination(features, rules)
        if reason is not None:
            raise InvalidPolicy(f"not structurally terminating: {reason}")
    except InvalidPolicy as error:
        return _failed_metrics(zero), f"invalid policy ({error})"

    policy = CompiledPolicy(features, rules)
    suites = {
        "train": TRAIN_INSTANCES,
        "large": LARGE_INSTANCES,
        "capacity": CAPACITY_INSTANCES,
        "initial": INITIAL_STATE_INSTANCES,
    }
    results = {name: [analyze_instance(policy, spec) for spec in specs] for name, specs in suites.items()}
    hard_names = {spec[0] for spec in _hard(LARGE_INSTANCES)}
    hard_results = [r for spec, r in zip(LARGE_INSTANCES, results["large"]) if spec[0] in hard_names]

    def coverage(rs: list[dict]) -> float:
        return sum(r["solved"] for r in rs) / len(rs)

    coverages = {
        "train_coverage": coverage(results["train"]),
        "large_instance_coverage": coverage(results["large"]),
        "hard_instance_coverage": coverage(hard_results),
        "capacity_shift_coverage": coverage(results["capacity"]),
        "initial_state_shift_coverage": coverage(results["initial"]),
    }
    all_results = [r for rs in results.values() for r in rs]
    failures = {}
    for r in all_results:
        if not r["solved"]:
            failures[r["reason"]] = failures.get(r["reason"], 0) + 1
    if failures:
        summary = ", ".join(f"{count} {kind}" for kind, count in sorted(failures.items()))
        return _failed_metrics(coverages), f"does not solve every instance ({summary})"

    held_out = results["large"] + results["capacity"] + results["initial"]
    counts = [c for r in held_out for c in r["branching"]]
    worst = [min(r["worst_ratio"], PLAN_RATIO_CAP) for r in held_out]
    metrics = {
        "policy_quality": sum(1.0 / r["expected_ratio"] for r in results["large"]) / len(results["large"]),
        "max_effective_width": max(r["undefined_fraction"] > 0 for r in results["large"]) * 1.0,
        "avg_effective_width": max(r["undefined_fraction"] for r in results["large"]),
        "max_applicable_successors": float(max(counts)),
        "avg_applicable_successors": sum(counts) / len(counts),
        "selected_features": min(float(len(features)), FEATURE_CAP),
        "policy_rules": min(float(len(rules)), RULE_CAP),
        "max_plan_length_ratio": max(worst),
        "avg_plan_length_ratio": sum(worst) / len(worst),
    }
    metrics.update(coverages)
    return metrics, "solves every instance"


# ---------------------------------------------------------------------------
# Baselines owned by the evaluator
# ---------------------------------------------------------------------------

BASELINES = {
    # Imitates only the first action of the example plans (pick).
    "one_step_imitation": {
        "selected_features": ["m_carried", "n_balls_at_a"],
        "rules": [{"condition": [], "effects": [["m_carried", "up"], ["n_balls_at_a", "down"]]}],
    },
    # Projects the five-ball example plan onto the seven named non-distractor
    # features, without feature selection or rule simplification.
    "plan_projection": {
        "selected_features": [
            "at_a", "goal", "m_carried", "n_balls_at_a", "remaining_work", "room_b", "space_in_gripper",
        ],
        "rules": [
            {
                "condition": [["at_a", "1"], ["goal", "0"], ["m_carried", "0"], ["n_balls_at_a", "1"],
                              ["remaining_work", "1"], ["room_b", "0"], ["space_in_gripper", "1"]],
                "effects": [["m_carried", "up"], ["n_balls_at_a", "down"], ["space_in_gripper", "down"]],
            },
            {
                "condition": [["at_a", "1"], ["goal", "0"], ["m_carried", "1"], ["n_balls_at_a", "1"],
                              ["remaining_work", "1"], ["room_b", "0"], ["space_in_gripper", "1"]],
                "effects": [["m_carried", "up"], ["n_balls_at_a", "down"], ["space_in_gripper", "down"]],
            },
            {
                "condition": [["at_a", "1"], ["goal", "0"], ["m_carried", "1"], ["n_balls_at_a", "1"],
                              ["remaining_work", "1"], ["room_b", "0"], ["space_in_gripper", "0"]],
                "effects": [["at_a", "false"], ["room_b", "true"]],
            },
            {
                "condition": [["at_a", "0"], ["goal", "0"], ["m_carried", "1"], ["n_balls_at_a", "1"],
                              ["remaining_work", "1"], ["room_b", "1"], ["space_in_gripper", "0"]],
                "effects": [["m_carried", "down"], ["remaining_work", "down"], ["space_in_gripper", "up"]],
            },
            {
                "condition": [["at_a", "0"], ["goal", "0"], ["m_carried", "1"], ["n_balls_at_a", "1"],
                              ["remaining_work", "1"], ["room_b", "1"], ["space_in_gripper", "1"]],
                "effects": [["m_carried", "down"], ["remaining_work", "down"], ["space_in_gripper", "up"]],
            },
            {
                "condition": [["at_a", "0"], ["goal", "0"], ["m_carried", "0"], ["n_balls_at_a", "1"],
                              ["remaining_work", "1"], ["room_b", "1"], ["space_in_gripper", "1"]],
                "effects": [["at_a", "true"], ["room_b", "false"]],
            },
            {
                "condition": [["at_a", "1"], ["goal", "0"], ["m_carried", "1"], ["n_balls_at_a", "0"],
                              ["remaining_work", "1"], ["room_b", "0"], ["space_in_gripper", "1"]],
                "effects": [["at_a", "false"], ["room_b", "true"]],
            },
            {
                "condition": [["at_a", "0"], ["goal", "0"], ["m_carried", "1"], ["n_balls_at_a", "0"],
                              ["remaining_work", "1"], ["room_b", "1"], ["space_in_gripper", "1"]],
                "effects": [["goal", "true"], ["m_carried", "down"], ["remaining_work", "down"],
                            ["space_in_gripper", "up"]],
            },
        ],
    },
    # Admits every legal successor (no features, one unconditional rule).
    "admit_all_legal": {
        "selected_features": [],
        "rules": [{"condition": [], "effects": []}],
    },
}
