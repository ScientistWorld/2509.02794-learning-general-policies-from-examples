"""Hidden test-slice evaluator for the Childsnack experiment.

Self-contained: this module owns the Childsnack dynamics, the dead-end test,
the semantics of every named feature, optimal plan lengths, the instances, and
the baseline policies. It imports nothing from `data/`, `method/` or
`eval/train/`. Policy parsing and the structural-termination gate are shared
with the Gripper evaluator of the same slice.

Abstract Childsnack (IPC 2014, one tray, three tables, exactly as many bread,
content and sandwich objects as children, and exactly as many gluten-free bread
and content portions as allergic children). State tuple:

    (gf_bread, reg_bread, gf_content, reg_content, unmade,
     gf_kitchen, reg_kitchen, gf_tray, reg_tray, gf_eaten,
     tray, allergic_per_table, nonallergic_per_table,
     children, allergic_total, seated_per_table)

A policy solves an instance iff every maximal policy trajectory from the
initial state is finite and ends in a goal state.
"""
from __future__ import annotations

import json
from collections import deque

from eval.test.evaluate_gripper import (
    CompiledPolicy,
    InvalidPolicy,
    parse_policy,
    structural_termination,
)

EXPERIMENT = "childsnack_generalization"
TABLES = 3
MAX_POLICY_STATES = 400_000  # per instance; beyond this the instance counts as unsolved
FEATURE_CAP = 20.0
RULE_CAP = 40.0

GB, RB, GC, RC, UNMADE, GK, RK, GT, RT, GE, TRAY, ALL, NON, KIDS, ATOT, SEATED = range(16)

# ---------------------------------------------------------------------------
# Instances: (name, allergic per table, non-allergic per table, initial resources)
# ---------------------------------------------------------------------------

# The ten learning instances (3 children each).
TRAIN_INSTANCES = [
    ("p-3-1.0-0.0-1-5", (0, 0, 0), (0, 1, 2), None),
    ("p-3-1.0-0.0-1-7", (0, 0, 0), (1, 2, 0), None),
    ("p-3-1.0-0.33-1-1", (0, 1, 0), (1, 1, 0), None),
    ("p-3-1.0-0.33-1-4", (0, 0, 1), (0, 2, 0), None),
    ("p-3-1.0-0.33-1-8", (1, 0, 0), (1, 0, 1), None),
    ("p-3-1.0-0.67-1-2", (0, 1, 1), (1, 0, 0), None),
    ("p-3-1.0-0.67-1-9", (0, 2, 0), (0, 0, 1), None),
    ("p-3-1.0-1.0-1-0", (1, 0, 2), (0, 0, 0), None),
    ("p-3-1.0-1.0-1-3", (1, 1, 1), (0, 0, 0), None),
    ("p-3-1.0-1.0-1-6", (1, 2, 0), (0, 0, 0), None),
]

# Held-out suites. Each entry is (allergic per table, non-allergic per table,
# initial resources). Initial resources are None for the generator's standard
# start (everything unmade in the kitchen, exact resources, tray in the
# kitchen), else (gf_bread, reg_bread, gf_content, reg_content, unmade,
# gf_kitchen, reg_kitchen, gf_tray, reg_tray, tray_place).
#
# size:     standard instances with 4-9 children (larger than the learning ones)
# resource: surplus ingredients or sandwich objects (generator constant factor > 1)
# initial:  some sandwiches already made (in the kitchen or on the tray) and/or
#           the tray starting at a table
_SIZE_SUITE = [
    ((0, 1, 0), (0, 1, 2), None),
    ((2, 0, 1), (0, 1, 0), None),
    ((1, 0, 0), (2, 1, 1), None),
    ((2, 1, 1), (0, 1, 0), None),
    ((1, 0, 1), (0, 2, 2), None),
    ((2, 1, 1), (2, 0, 0), None),
    ((0, 2, 0), (3, 1, 1), None),
    ((1, 3, 1), (0, 1, 1), None),
    ((0, 2, 0), (2, 3, 1), None),
    ((2, 1, 3), (0, 0, 2), None),
    ((0, 1, 1), (3, 2, 2), None),
    ((1, 5, 1), (1, 0, 1), None),
]
_RESOURCE_SUITE = [
    ((0, 1, 1), (1, 1, 3), (3, 7, 3, 7, 7, 0, 0, 0, 0, 0)),
    ((2, 0, 0), (0, 4, 0), (4, 4, 2, 4, 7, 0, 0, 0, 0, 0)),
    ((1, 0, 2), (0, 1, 0), (4, 3, 3, 2, 4, 0, 0, 0, 0, 0)),
    ((4, 0, 0), (0, 0, 2), (4, 3, 4, 2, 6, 0, 0, 0, 0, 0)),
    ((5, 0, 0), (0, 1, 1), (7, 2, 5, 2, 8, 0, 0, 0, 0, 0)),
    ((0, 0, 1), (2, 2, 0), (2, 4, 1, 6, 5, 0, 0, 0, 0, 0)),
    ((1, 0, 1), (0, 3, 0), (2, 4, 4, 4, 5, 0, 0, 0, 0, 0)),
    ((2, 0, 2), (0, 2, 0), (4, 2, 4, 3, 6, 0, 0, 0, 0, 0)),
    ((2, 1, 1), (2, 1, 0), (4, 5, 6, 4, 7, 0, 0, 0, 0, 0)),
    ((1, 1, 0), (0, 0, 2), (4, 4, 2, 3, 6, 0, 0, 0, 0, 0)),
    ((1, 0, 0), (2, 0, 2), (1, 6, 3, 4, 5, 0, 0, 0, 0, 0)),
    ((0, 1, 0), (1, 2, 0), (2, 5, 1, 5, 4, 0, 0, 0, 0, 0)),
]
_INITIAL_SUITE = [
    ((0, 3, 2), (1, 0, 1), (3, 0, 3, 0, 3, 0, 0, 2, 2, 1)),
    ((1, 1, 2), (1, 0, 0), (2, 1, 2, 1, 3, 0, 0, 2, 0, 0)),
    ((0, 1, 0), (2, 2, 0), (1, 2, 1, 2, 3, 0, 0, 0, 2, 1)),
    ((0, 2, 0), (0, 3, 0), (1, 3, 1, 3, 4, 1, 0, 0, 0, 3)),
    ((3, 1, 1), (0, 0, 2), (4, 1, 4, 1, 5, 1, 1, 0, 0, 3)),
    ((0, 0, 2), (1, 2, 0), (2, 2, 2, 2, 4, 0, 0, 0, 1, 1)),
    ((1, 0, 1), (3, 1, 1), (0, 3, 0, 3, 3, 2, 2, 0, 0, 3)),
    ((1, 0, 0), (1, 2, 1), (1, 3, 1, 3, 4, 0, 1, 0, 0, 3)),
    ((2, 1, 0), (1, 0, 0), (3, 1, 3, 1, 4, 0, 0, 0, 0, 3)),
    ((1, 0, 1), (1, 2, 1), (2, 3, 2, 3, 5, 0, 1, 0, 0, 2)),
    ((0, 1, 1), (0, 2, 1), (1, 2, 1, 2, 3, 1, 1, 0, 0, 2)),
    ((2, 0, 0), (1, 3, 0), (0, 2, 0, 2, 2, 2, 2, 0, 0, 3)),
]

def _suite(label: str, entries: list) -> list[tuple]:
    return [(f"{label}_{i:02d}", a, n, init) for i, (a, n, init) in enumerate(entries)]


SUITES = {
    "size": _suite("size", _SIZE_SUITE),
    "resource": _suite("resource", _RESOURCE_SUITE),
    "initial": _suite("initial", _INITIAL_SUITE),
}
HELD_OUT_INSTANCES = [spec for suite in SUITES.values() for spec in suite]

# ---------------------------------------------------------------------------
# Dynamics
# ---------------------------------------------------------------------------


def _initial(spec: tuple) -> tuple:
    _, allergic, nonallergic, init = spec
    a = sum(allergic)
    c = a + sum(nonallergic)
    seated = tuple(x + y for x, y in zip(allergic, nonallergic))
    if init is None:
        init = (a, c - a, a, c - a, c, 0, 0, 0, 0, 0)
    gb, rb, gc, rc, unmade, gk, rk, gt, rt, tray = init
    return (gb, rb, gc, rc, unmade, gk, rk, gt, rt, 0, tray, tuple(allergic), tuple(nonallergic), c, a, seated)


def _unserved(s: tuple) -> int:
    return sum(s[ALL]) + sum(s[NON])


def _is_goal(s: tuple) -> bool:
    return _unserved(s) == 0


def _with(s: tuple, **changes) -> tuple:
    out = list(s)
    for key, value in changes.items():
        out[globals()[key]] = value
    return tuple(out)


def _successors(s: tuple) -> list[tuple]:
    out = []
    if s[UNMADE] > 0:
        if s[GB] > 0 and s[GC] > 0:  # make_sandwich_no_gluten
            out.append(_with(s, GB=s[GB] - 1, GC=s[GC] - 1, UNMADE=s[UNMADE] - 1, GK=s[GK] + 1))
        for bread in (RB, GB):  # make_sandwich (not gluten-free), any ingredients
            for content in (RC, GC):
                if s[bread] > 0 and s[content] > 0:
                    t = list(s)
                    t[bread] -= 1
                    t[content] -= 1
                    t[UNMADE] -= 1
                    t[RK] += 1
                    out.append(tuple(t))
    if s[TRAY] == 0:
        if s[GK] > 0:
            out.append(_with(s, GK=s[GK] - 1, GT=s[GT] + 1))
        if s[RK] > 0:
            out.append(_with(s, RK=s[RK] - 1, RT=s[RT] + 1))
    else:
        j = s[TRAY] - 1
        if s[ALL][j] > 0 and s[GT] > 0:
            allergic = s[ALL][:j] + (s[ALL][j] - 1,) + s[ALL][j + 1:]
            out.append(_with(s, ALL=allergic, GT=s[GT] - 1, GE=s[GE] + 1))
        if s[NON][j] > 0:
            nonallergic = s[NON][:j] + (s[NON][j] - 1,) + s[NON][j + 1:]
            if s[RT] > 0:
                out.append(_with(s, NON=nonallergic, RT=s[RT] - 1))
            if s[GT] > 0:
                out.append(_with(s, NON=nonallergic, GT=s[GT] - 1, GE=s[GE] + 1))
    for place in range(TABLES + 1):
        if place != s[TRAY]:
            out.append(_with(s, TRAY=place))
    return out


def _is_dead_end(s: tuple) -> bool:
    if _is_goal(s):
        return False
    gf_ready = s[GK] + s[GT]
    all_ready = gf_ready + s[RK] + s[RT]
    gf_makeable = min(s[GB], s[GC], s[UNMADE])
    makeable = min(s[GB] + s[RB], s[GC] + s[RC], s[UNMADE])
    return sum(s[ALL]) > gf_ready + gf_makeable or _unserved(s) > all_ready + makeable


def _optimal_length(spec: tuple) -> int:
    """Length of an optimal plan from the instance's initial state.

    For the standard start, each child needs its own make, put-on-tray and
    serve, and each occupied table one tray move. Otherwise breadth-first search.
    """
    start = _initial(spec)
    if spec[3] is None:
        return 3 * start[KIDS] + sum(1 for k in start[SEATED] if k > 0)
    if _is_goal(start):
        return 0
    depth = {start: 0}
    frontier = deque([start])
    while frontier:
        state = frontier.popleft()
        for nxt in _successors(state):
            if nxt in depth or _is_dead_end(nxt):
                continue
            depth[nxt] = depth[state] + 1
            if _is_goal(nxt):
                return depth[nxt]
            frontier.append(nxt)
    raise RuntimeError(f"unsolvable held-out instance {spec[0]}")


# ---------------------------------------------------------------------------
# Feature pool: name -> (kind, function of state)
# ---------------------------------------------------------------------------


def _at_tray(s: tuple, which: str) -> int:
    if s[TRAY] == 0:
        return 0
    j = s[TRAY] - 1
    if which == "allergic":
        return s[ALL][j]
    if which == "nonallergic":
        return s[NON][j]
    if which == "seated":
        return s[SEATED][j]
    return s[ALL][j] + s[NON][j]


def _build_pool() -> dict:
    pool = {
        "bread_at_kitchen": ("num", lambda s: s[GB] + s[RB]),
        "content_at_kitchen": ("num", lambda s: s[GC] + s[RC]),
        "sandwiches_at_kitchen": ("num", lambda s: s[GK] + s[RK]),
        "unmade_sandwiches": ("num", lambda s: s[UNMADE]),
        "served_children": ("num", lambda s: s[KIDS] - _unserved(s)),
        "gf_sandwiches": ("num", lambda s: s[GK] + s[GT] + s[GE]),
        "tray_at_kitchen": ("bool", lambda s: s[TRAY] == 0),
        "sandwiches_on_tray": ("num", lambda s: s[GT] + s[RT]),
        "gf_bread_at_kitchen": ("num", lambda s: s[GB]),
        "gf_content_at_kitchen": ("num", lambda s: s[GC]),
        "gf_sandwiches_at_kitchen": ("num", lambda s: s[GK]),
        "unserved_children": ("num", lambda s: _unserved(s)),
        "served_allergic": ("num", lambda s: s[ATOT] - sum(s[ALL])),
        "served_nonallergic": ("num", lambda s: (s[KIDS] - s[ATOT]) - sum(s[NON])),
        "goal": ("bool", lambda s: _unserved(s) == 0),
        "gf_sandwiches_on_tray": ("num", lambda s: s[GT]),
        "unserved_allergic": ("num", lambda s: sum(s[ALL])),
        "unserved_nonallergic": ("num", lambda s: sum(s[NON])),
        "reg_bread_at_kitchen": ("num", lambda s: s[RB]),
        "reg_content_at_kitchen": ("num", lambda s: s[RC]),
        "reg_sandwiches_at_kitchen": ("num", lambda s: s[RK]),
        "reg_sandwiches_on_tray": ("num", lambda s: s[RT]),
        "tables_with_unserved": ("num", lambda s: sum(1 for a, n in zip(s[ALL], s[NON]) if a + n > 0)),
        "seated_at_tray_table": ("num", lambda s: _at_tray(s, "seated")),
        "tray_at_table_with_unserved": ("bool", lambda s: _at_tray(s, "all") > 0),
        "waiting_at_tray": ("num", lambda s: _at_tray(s, "all")),
        "allergic_waiting_at_tray": ("num", lambda s: _at_tray(s, "allergic")),
        "nonallergic_waiting_at_tray": ("num", lambda s: _at_tray(s, "nonallergic")),
    }
    for i in range(120):
        mod = 2 + (i % 7)
        offset = i // 7
        pool[f"distractor_{i:03d}"] = (
            "num",
            lambda s, mod=mod, offset=offset: (s[KIDS] * (offset + 1) + _unserved(s)) % mod,
        )
    return pool


POOL = _build_pool()

# ---------------------------------------------------------------------------
# Policy execution over all policy trajectories
# ---------------------------------------------------------------------------


def analyze_instance(policy: CompiledPolicy, spec: tuple) -> dict:
    start = _initial(spec)
    graph: dict = {}
    frontier = deque([start])
    seen = {start}
    undefined_alive = 0
    alive = 0
    reached_dead_end = False
    while frontier:
        state = frontier.popleft()
        if _is_goal(state):
            graph[state] = []
            continue
        admitted = [t for t in _successors(state) if policy.admits(state, t)]
        graph[state] = admitted
        if _is_dead_end(state):
            reached_dead_end = True
        else:
            alive += 1
            if not admitted:
                undefined_alive += 1
        for nxt in admitted:
            if nxt not in seen:
                if len(seen) >= MAX_POLICY_STATES:
                    return {"solved": False, "reason": "state budget", "undefined_fraction": 1.0}
                seen.add(nxt)
                frontier.append(nxt)
    indegree = {s: 0 for s in graph}
    for succ in graph.values():
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
    stuck = any(not succ and not _is_goal(s) for s, succ in graph.items())
    solved = acyclic and not stuck
    if solved:
        reason = "solved"
    elif not acyclic:
        reason = "cycle"
    elif reached_dead_end:
        reason = "dead end"
    else:
        reason = "undefined"
    result = {
        "solved": solved,
        "reason": reason,
        "undefined_fraction": undefined_alive / alive if alive else 0.0,
    }
    if solved:
        expected: dict = {}
        for s in reversed(order):
            succ = graph[s]
            expected[s] = 0.0 if not succ else 1.0 + sum(expected[t] for t in succ) / len(succ)
        optimal = _optimal_length(spec)
        result["quality"] = optimal / expected[start] if expected[start] > 0 else 1.0
    return result


def _failed_metrics(coverages: dict) -> dict:
    metrics = {
        "policy_quality": 0.0,
        "max_effective_width": 1.0,
        "avg_effective_width": 1.0,
        "selected_features": FEATURE_CAP,
        "policy_rules": RULE_CAP,
    }
    metrics.update(coverages)
    return metrics


def evaluate_payload(payload) -> tuple[dict, str]:
    zero = {
        "heldout_coverage": 0.0,
        "size_coverage": 0.0,
        "resource_shift_coverage": 0.0,
        "initial_state_shift_coverage": 0.0,
        "train_coverage": 0.0,
    }
    try:
        features, rules = parse_policy(payload, POOL)
        reason = structural_termination(features, rules)
        if reason is not None:
            raise InvalidPolicy(f"not structurally terminating: {reason}")
    except InvalidPolicy as error:
        return _failed_metrics(zero), f"invalid policy ({error})"

    policy = CompiledPolicy(features, rules, POOL)
    train = [analyze_instance(policy, spec) for spec in TRAIN_INSTANCES]
    by_suite = {label: [analyze_instance(policy, spec) for spec in specs] for label, specs in SUITES.items()}
    held_out = [r for rs in by_suite.values() for r in rs]

    def coverage(rs: list[dict]) -> float:
        return sum(r["solved"] for r in rs) / len(rs)

    coverages = {
        "heldout_coverage": coverage(held_out),
        "size_coverage": coverage(by_suite["size"]),
        "resource_shift_coverage": coverage(by_suite["resource"]),
        "initial_state_shift_coverage": coverage(by_suite["initial"]),
        "train_coverage": coverage(train),
    }
    failures: dict = {}
    for r in held_out:
        if not r["solved"]:
            failures[r["reason"]] = failures.get(r["reason"], 0) + 1
    summary = ", ".join(f"{count} {kind}" for kind, count in sorted(failures.items())) or "none"
    if coverages["train_coverage"] < 1.0:
        return _failed_metrics(coverages), f"does not solve its learning instances (held-out failures: {summary})"
    metrics = {
        "policy_quality": sum(r.get("quality", 0.0) for r in held_out) / len(held_out),
        "max_effective_width": max(r["undefined_fraction"] > 0 for r in held_out) * 1.0,
        "avg_effective_width": sum(r["undefined_fraction"] for r in held_out) / len(held_out),
        "selected_features": min(float(len(features)), FEATURE_CAP),
        "policy_rules": min(float(len(rules)), RULE_CAP),
    }
    metrics.update(coverages)
    return metrics, f"solves {sum(r['solved'] for r in held_out)}/{len(held_out)} held-out (failures: {summary})"


# ---------------------------------------------------------------------------
# Baselines owned by the evaluator
# ---------------------------------------------------------------------------

# Projection of the first example-plan transition (make a gluten-free sandwich)
# onto two features it changes, with no conditions.
_ONE_STEP = {
    "selected_features": ["sandwiches_at_kitchen", "unmade_sandwiches"],
    "rules": [{"condition": [], "effects": [["sandwiches_at_kitchen", "up"], ["unmade_sandwiches", "down"]]}],
}
# The example plan of learning instance p-3-1.0-0.67-1-2 projected onto every
# named non-distractor feature, with full conditions and no simplification.
_PLAN_PROJECTION = json.loads(
    """{"selected_features":["allergic_waiting_at_tray","bread_at_kitchen","content_at_kitchen","gf_bread_at_kitchen","gf_content_at_kitchen","gf_sandwiches","gf_sandwiches_at_kitchen","gf_sandwiches_on_tray","goal","nonallergic_waiting_at_tray","reg_bread_at_kitchen","reg_content_at_kitchen","reg_sandwiches_at_kitchen","reg_sandwiches_on_tray","sandwiches_at_kitchen","sandwiches_on_tray","seated_at_tray_table","served_allergic","served_children","served_nonallergic","tables_with_unserved","tray_at_kitchen","tray_at_table_with_unserved","unmade_sandwiches","unserved_allergic","unserved_children","unserved_nonallergic","waiting_at_tray"],"rules":[{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","1"],["content_at_kitchen","1"],["gf_bread_at_kitchen","1"],["gf_content_at_kitchen","1"],["gf_sandwiches","0"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","0"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","1"],["reg_content_at_kitchen","1"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","0"],["sandwiches_on_tray","0"],["seated_at_tray_table","0"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","1"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","1"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","0"]],"effects":[["bread_at_kitchen","down"],["content_at_kitchen","down"],["gf_bread_at_kitchen","down"],["gf_content_at_kitchen","down"],["gf_sandwiches","up"],["gf_sandwiches_at_kitchen","up"],["sandwiches_at_kitchen","up"],["unmade_sandwiches","down"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","1"],["content_at_kitchen","1"],["gf_bread_at_kitchen","1"],["gf_content_at_kitchen","1"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","1"],["gf_sandwiches_on_tray","0"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","1"],["reg_content_at_kitchen","1"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","1"],["sandwiches_on_tray","0"],["seated_at_tray_table","0"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","1"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","1"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","0"]],"effects":[["bread_at_kitchen","down"],["content_at_kitchen","down"],["gf_bread_at_kitchen","down"],["gf_content_at_kitchen","down"],["gf_sandwiches","up"],["gf_sandwiches_at_kitchen","up"],["sandwiches_at_kitchen","up"],["unmade_sandwiches","down"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","1"],["content_at_kitchen","1"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","1"],["gf_sandwiches_on_tray","0"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","1"],["reg_content_at_kitchen","1"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","1"],["sandwiches_on_tray","0"],["seated_at_tray_table","0"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","1"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","1"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","0"]],"effects":[["bread_at_kitchen","down"],["content_at_kitchen","down"],["reg_bread_at_kitchen","down"],["reg_content_at_kitchen","down"],["reg_sandwiches_at_kitchen","up"],["sandwiches_at_kitchen","up"],["unmade_sandwiches","down"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","1"],["gf_sandwiches_on_tray","0"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","1"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","1"],["sandwiches_on_tray","0"],["seated_at_tray_table","0"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","1"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","0"]],"effects":[["gf_sandwiches_at_kitchen","down"],["gf_sandwiches_on_tray","up"],["sandwiches_at_kitchen","down"],["sandwiches_on_tray","up"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","1"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","1"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","1"],["sandwiches_on_tray","1"],["seated_at_tray_table","0"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","1"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","0"]],"effects":[["gf_sandwiches_at_kitchen","down"],["gf_sandwiches_on_tray","up"],["sandwiches_at_kitchen","down"],["sandwiches_on_tray","up"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","1"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","1"],["sandwiches_on_tray","1"],["seated_at_tray_table","0"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","1"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","0"]],"effects":[["reg_sandwiches_at_kitchen","down"],["reg_sandwiches_on_tray","up"],["sandwiches_at_kitchen","down"],["sandwiches_on_tray","up"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","1"],["sandwiches_at_kitchen","0"],["sandwiches_on_tray","1"],["seated_at_tray_table","0"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","1"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","0"]],"effects":[["nonallergic_waiting_at_tray","up"],["seated_at_tray_table","up"],["tray_at_kitchen","false"],["tray_at_table_with_unserved","true"],["waiting_at_tray","up"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","1"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","1"],["sandwiches_at_kitchen","0"],["sandwiches_on_tray","1"],["seated_at_tray_table","1"],["served_allergic","0"],["served_children","0"],["served_nonallergic","0"],["tables_with_unserved","1"],["tray_at_kitchen","0"],["tray_at_table_with_unserved","1"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","1"],["waiting_at_tray","1"]],"effects":[["nonallergic_waiting_at_tray","down"],["reg_sandwiches_on_tray","down"],["sandwiches_on_tray","down"],["served_children","up"],["served_nonallergic","up"],["tables_with_unserved","down"],["tray_at_table_with_unserved","false"],["unserved_children","down"],["unserved_nonallergic","down"],["waiting_at_tray","down"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","0"],["sandwiches_on_tray","1"],["seated_at_tray_table","1"],["served_allergic","0"],["served_children","1"],["served_nonallergic","1"],["tables_with_unserved","1"],["tray_at_kitchen","0"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","0"],["waiting_at_tray","0"]],"effects":[["allergic_waiting_at_tray","up"],["tray_at_table_with_unserved","true"],["waiting_at_tray","up"]]},{"condition":[["allergic_waiting_at_tray","1"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","0"],["sandwiches_on_tray","1"],["seated_at_tray_table","1"],["served_allergic","0"],["served_children","1"],["served_nonallergic","1"],["tables_with_unserved","1"],["tray_at_kitchen","0"],["tray_at_table_with_unserved","1"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","0"],["waiting_at_tray","1"]],"effects":[["allergic_waiting_at_tray","down"],["gf_sandwiches_on_tray","down"],["sandwiches_on_tray","down"],["served_allergic","up"],["served_children","up"],["tables_with_unserved","down"],["tray_at_table_with_unserved","false"],["unserved_allergic","down"],["unserved_children","down"],["waiting_at_tray","down"]]},{"condition":[["allergic_waiting_at_tray","0"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","0"],["sandwiches_on_tray","1"],["seated_at_tray_table","1"],["served_allergic","1"],["served_children","1"],["served_nonallergic","1"],["tables_with_unserved","1"],["tray_at_kitchen","0"],["tray_at_table_with_unserved","0"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","0"],["waiting_at_tray","0"]],"effects":[["allergic_waiting_at_tray","up"],["tray_at_table_with_unserved","true"],["waiting_at_tray","up"]]},{"condition":[["allergic_waiting_at_tray","1"],["bread_at_kitchen","0"],["content_at_kitchen","0"],["gf_bread_at_kitchen","0"],["gf_content_at_kitchen","0"],["gf_sandwiches","1"],["gf_sandwiches_at_kitchen","0"],["gf_sandwiches_on_tray","1"],["goal","0"],["nonallergic_waiting_at_tray","0"],["reg_bread_at_kitchen","0"],["reg_content_at_kitchen","0"],["reg_sandwiches_at_kitchen","0"],["reg_sandwiches_on_tray","0"],["sandwiches_at_kitchen","0"],["sandwiches_on_tray","1"],["seated_at_tray_table","1"],["served_allergic","1"],["served_children","1"],["served_nonallergic","1"],["tables_with_unserved","1"],["tray_at_kitchen","0"],["tray_at_table_with_unserved","1"],["unmade_sandwiches","0"],["unserved_allergic","1"],["unserved_children","1"],["unserved_nonallergic","0"],["waiting_at_tray","1"]],"effects":[["allergic_waiting_at_tray","down"],["gf_sandwiches_on_tray","down"],["goal","true"],["sandwiches_on_tray","down"],["served_allergic","up"],["served_children","up"],["tables_with_unserved","down"],["tray_at_table_with_unserved","false"],["unserved_allergic","down"],["unserved_children","down"],["waiting_at_tray","down"]]}]}"""
)
BASELINES = {
    "one_step_imitation": _ONE_STEP,
    "plan_projection": _PLAN_PROJECTION,
    # Admits every legal successor (no features, one unconditional rule).
    "admit_all_legal": {"selected_features": [], "rules": [{"condition": [], "effects": []}]},
}
