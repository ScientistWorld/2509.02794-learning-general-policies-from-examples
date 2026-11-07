"""Childsnack domain for learning generalized policies (method-side resources).

Abstraction of the IPC 2014 Childsnack domain used in the paper's experiments
(one tray, three tables, the "constant factor 1.0" generator: exactly as many
bread portions, content portions and sandwich objects as children, and exactly
as many gluten-free bread and content portions as allergic children).

The state abstracts object identities into counts:

- gluten-free / regular bread and content portions still in the kitchen,
- sandwiches not yet made, made and in the kitchen, or on the tray (each split
  into gluten-free and regular), and gluten-free sandwiches already eaten,
- the tray's place (0 = kitchen, 1..3 = table),
- per table, the allergic and the non-allergic children still waiting.

Actions follow the PDDL domain: `make_sandwich_no_gluten` (gluten-free bread
and content, gives a gluten-free sandwich), `make_sandwich` (any bread and
content, gives a sandwich that is NOT gluten-free), `put_on_tray` (tray in the
kitchen), `serve_sandwich_no_gluten` (allergic child, gluten-free sandwich),
`serve_sandwich` (non-allergic child, any sandwich), and `move_tray` between any
two places. Wasting a gluten-free ingredient or sandwich creates a dead end.

This module provides what a learner may use: the dynamics, an optimal
planner that returns example plans, the named feature pool, and the paper's
training instances. Held-out evaluation instances are not part of this module;
the evaluator owns its own copy of the dynamics, feature semantics and instances.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Iterable

from data.policy_features import (
    Feature,
    Transition,
    changes_differ,
    effect,
    transition_change,
    valuation,
)

TABLES = 3

__all__ = [
    "Feature",
    "Instance",
    "State",
    "Transition",
    "TABLES",
    "changes_differ",
    "effect",
    "feature_pool",
    "is_dead_end",
    "planner",
    "planner_from_state",
    "successors",
    "training_instances",
    "transition_change",
    "valuation",
]


@dataclass(frozen=True)
class State:
    gf_bread: int
    reg_bread: int
    gf_content: int
    reg_content: int
    unmade: int
    gf_kitchen: int
    reg_kitchen: int
    gf_tray: int
    reg_tray: int
    gf_eaten: int
    tray: int  # 0 = kitchen, 1..TABLES = table
    allergic: tuple[int, ...]  # unserved allergic children per table
    nonallergic: tuple[int, ...]  # unserved non-allergic children per table
    children: int
    allergic_total: int
    seated: tuple[int, ...] = ()  # children seated per table (static)

    def unserved(self) -> int:
        return sum(self.allergic) + sum(self.nonallergic)

    def is_goal(self) -> bool:
        return self.unserved() == 0

    def key(self) -> tuple:
        return (
            self.gf_bread, self.reg_bread, self.gf_content, self.reg_content, self.unmade,
            self.gf_kitchen, self.reg_kitchen, self.gf_tray, self.reg_tray, self.gf_eaten,
            self.tray, self.allergic, self.nonallergic, self.children, self.allergic_total, self.seated,
        )


@dataclass(frozen=True)
class Instance:
    """A Childsnack instance: per-table counts of allergic / non-allergic children."""

    name: str
    allergic: tuple[int, ...]
    nonallergic: tuple[int, ...]

    def initial(self) -> State:
        a = sum(self.allergic)
        c = a + sum(self.nonallergic)
        seated = tuple(x + y for x, y in zip(self.allergic, self.nonallergic))
        return State(a, c - a, a, c - a, c, 0, 0, 0, 0, 0, 0, tuple(self.allergic), tuple(self.nonallergic), c, a, seated)


def successors(state: State) -> list[Transition]:
    """All applicable ground actions, up to object symmetry, in a fixed order."""
    s = state
    out: list[Transition] = []
    if s.unmade > 0:
        if s.gf_bread > 0 and s.gf_content > 0:
            out.append(Transition(s, replace(s, gf_bread=s.gf_bread - 1, gf_content=s.gf_content - 1,
                                             unmade=s.unmade - 1, gf_kitchen=s.gf_kitchen + 1),
                                  "make_sandwich_no_gluten"))
        for bread in ("reg", "gf"):
            for content in ("reg", "gf"):
                if getattr(s, f"{bread}_bread") > 0 and getattr(s, f"{content}_content") > 0:
                    changes = {
                        f"{bread}_bread": getattr(s, f"{bread}_bread") - 1,
                        f"{content}_content": getattr(s, f"{content}_content") - 1,
                    }
                    out.append(Transition(s, replace(s, unmade=s.unmade - 1, reg_kitchen=s.reg_kitchen + 1, **changes),
                                          f"make_sandwich[{bread}_bread,{content}_content]"))
    if s.tray == 0:
        if s.gf_kitchen > 0:
            out.append(Transition(s, replace(s, gf_kitchen=s.gf_kitchen - 1, gf_tray=s.gf_tray + 1), "put_on_tray[gf]"))
        if s.reg_kitchen > 0:
            out.append(Transition(s, replace(s, reg_kitchen=s.reg_kitchen - 1, reg_tray=s.reg_tray + 1), "put_on_tray[reg]"))
    else:
        j = s.tray - 1
        if s.allergic[j] > 0 and s.gf_tray > 0:
            allergic = s.allergic[:j] + (s.allergic[j] - 1,) + s.allergic[j + 1:]
            out.append(Transition(s, replace(s, allergic=allergic, gf_tray=s.gf_tray - 1, gf_eaten=s.gf_eaten + 1),
                                  "serve_sandwich_no_gluten"))
        if s.nonallergic[j] > 0:
            nonallergic = s.nonallergic[:j] + (s.nonallergic[j] - 1,) + s.nonallergic[j + 1:]
            if s.reg_tray > 0:
                out.append(Transition(s, replace(s, nonallergic=nonallergic, reg_tray=s.reg_tray - 1),
                                      "serve_sandwich[reg]"))
            if s.gf_tray > 0:
                out.append(Transition(s, replace(s, nonallergic=nonallergic, gf_tray=s.gf_tray - 1,
                                                 gf_eaten=s.gf_eaten + 1), "serve_sandwich[gf]"))
    for place in range(TABLES + 1):
        if place != s.tray:
            out.append(Transition(s, replace(s, tray=place), f"move_tray[{s.tray}->{place}]"))
    return out


def is_dead_end(state: State) -> bool:
    """Exact test: can every waiting child still be served?

    Allergic children need gluten-free sandwiches (existing or makeable from
    gluten-free bread and content); every child needs some sandwich.
    """
    s = state
    if s.is_goal():
        return False
    gf_ready = s.gf_kitchen + s.gf_tray
    all_ready = gf_ready + s.reg_kitchen + s.reg_tray
    gf_makeable = min(s.gf_bread, s.gf_content, s.unmade)
    makeable = min(s.gf_bread + s.reg_bread, s.gf_content + s.reg_content, s.unmade)
    return sum(s.allergic) > gf_ready + gf_makeable or s.unserved() > all_ready + makeable


def planner_from_state(state: State) -> list[Transition]:
    """Optimal planner: breadth-first search with a fixed successor order.

    Returns a shortest plan to the goal (ties broken by the successor order)
    and raises RuntimeError on dead-end states.
    """
    if state.is_goal():
        return []
    if is_dead_end(state):
        raise RuntimeError(f"no plan from dead-end state {state}")
    parents: dict[tuple, tuple[tuple, Transition] | None] = {state.key(): None}
    frontier = deque([state])
    while frontier:
        current = frontier.popleft()
        for transition in successors(current):
            nxt = transition.target
            if nxt.key() in parents or is_dead_end(nxt):
                continue
            parents[nxt.key()] = (current.key(), transition)
            if nxt.is_goal():
                path: list[Transition] = []
                key = nxt.key()
                while parents[key] is not None:
                    prev, step = parents[key]
                    path.append(step)
                    key = prev
                return list(reversed(path))
            frontier.append(nxt)
    raise RuntimeError(f"no plan from state {state}")


def planner(instance: Instance) -> list[Transition]:
    return planner_from_state(instance.initial())


def _at_tray(s: State, which: str) -> int:
    if s.tray == 0:
        return 0
    j = s.tray - 1
    if which == "allergic":
        return s.allergic[j]
    if which == "nonallergic":
        return s.nonallergic[j]
    return s.allergic[j] + s.nonallergic[j]


def _seated_at_tray(s: State) -> int:
    """Children (served or not) seated at the tray's table: |exists waiting.(exists at^-1.T)|."""
    if s.tray == 0:
        return 0
    return s.seated[s.tray - 1]


def feature_pool(extra_distractors: int = 120) -> list[Feature]:
    """Named feature pool (description-logic style concept counts).

    The evaluator defines the same names independently.
    """
    features = [
        Feature("bread_at_kitchen", "num", 1, lambda s: s.gf_bread + s.reg_bread),
        Feature("content_at_kitchen", "num", 1, lambda s: s.gf_content + s.reg_content),
        Feature("sandwiches_at_kitchen", "num", 1, lambda s: s.gf_kitchen + s.reg_kitchen),
        Feature("unmade_sandwiches", "num", 1, lambda s: s.unmade),
        Feature("served_children", "num", 1, lambda s: s.children - s.unserved()),
        Feature("gf_sandwiches", "num", 1, lambda s: s.gf_kitchen + s.gf_tray + s.gf_eaten),
        Feature("tray_at_kitchen", "bool", 2, lambda s: s.tray == 0),
        Feature("sandwiches_on_tray", "num", 2, lambda s: s.gf_tray + s.reg_tray),
        Feature("gf_bread_at_kitchen", "num", 2, lambda s: s.gf_bread),
        Feature("gf_content_at_kitchen", "num", 2, lambda s: s.gf_content),
        Feature("gf_sandwiches_at_kitchen", "num", 2, lambda s: s.gf_kitchen),
        Feature("unserved_children", "num", 2, lambda s: s.unserved()),
        Feature("served_allergic", "num", 2, lambda s: s.allergic_total - sum(s.allergic)),
        Feature("served_nonallergic", "num", 2,
                lambda s: (s.children - s.allergic_total) - sum(s.nonallergic)),
        Feature("goal", "bool", 2, lambda s: s.is_goal()),
        Feature("gf_sandwiches_on_tray", "num", 3, lambda s: s.gf_tray),
        Feature("unserved_allergic", "num", 3, lambda s: sum(s.allergic)),
        Feature("unserved_nonallergic", "num", 3, lambda s: sum(s.nonallergic)),
        Feature("reg_bread_at_kitchen", "num", 3, lambda s: s.reg_bread),
        Feature("reg_content_at_kitchen", "num", 3, lambda s: s.reg_content),
        Feature("reg_sandwiches_at_kitchen", "num", 3, lambda s: s.reg_kitchen),
        Feature("reg_sandwiches_on_tray", "num", 4, lambda s: s.reg_tray),
        Feature("tables_with_unserved", "num", 4,
                lambda s: sum(1 for a, n in zip(s.allergic, s.nonallergic) if a + n > 0)),
        Feature("seated_at_tray_table", "num", 4, lambda s: _seated_at_tray(s)),
        Feature("tray_at_table_with_unserved", "bool", 5, lambda s: _at_tray(s, "all") > 0),
        Feature("waiting_at_tray", "num", 5, lambda s: _at_tray(s, "all")),
        Feature("allergic_waiting_at_tray", "num", 6, lambda s: _at_tray(s, "allergic")),
        Feature("nonallergic_waiting_at_tray", "num", 6, lambda s: _at_tray(s, "nonallergic")),
    ]
    for i in range(extra_distractors):
        mod = 2 + (i % 7)
        offset = i // 7
        features.append(
            Feature(
                f"distractor_{i:03d}",
                "num",
                5 + (i % 5),
                lambda s, mod=mod, offset=offset: (s.children * (offset + 1) + s.unserved()) % mod,
            )
        )
    return features


# The paper's Childsnack training set Q (Table 1: |Q| = 10): the ten 3-children
# instances p-3-1.0-{0.0,0.33,0.67,1.0}-1-* of learning/benchmarks/tractable/
# childsnack/training/easy in the authors' release (one tray, three tables,
# constant factor 1.0), in file order. Seatings are (allergic per table,
# non-allergic per table).
_TRAINING_SEATINGS = [
    ("p-3-1.0-0.0-1-5", (0, 0, 0), (0, 1, 2)),
    ("p-3-1.0-0.0-1-7", (0, 0, 0), (1, 2, 0)),
    ("p-3-1.0-0.33-1-1", (0, 1, 0), (1, 1, 0)),
    ("p-3-1.0-0.33-1-4", (0, 0, 1), (0, 2, 0)),
    ("p-3-1.0-0.33-1-8", (1, 0, 0), (1, 0, 1)),
    ("p-3-1.0-0.67-1-2", (0, 1, 1), (1, 0, 0)),
    ("p-3-1.0-0.67-1-9", (0, 2, 0), (0, 0, 1)),
    ("p-3-1.0-1.0-1-0", (1, 0, 2), (0, 0, 0)),
    ("p-3-1.0-1.0-1-3", (1, 1, 1), (0, 0, 0)),
    ("p-3-1.0-1.0-1-6", (1, 2, 0), (0, 0, 0)),
]


def training_instances() -> list[Instance]:
    """The paper's ten Childsnack learning instances (3 children each)."""
    return [Instance(name, a, n) for name, a, n in _TRAINING_SEATINGS]


def all_states(instance: Instance) -> Iterable[State]:
    """Every state reachable from the instance's initial state (small instances only)."""
    start = instance.initial()
    seen = {start.key(): start}
    frontier = deque([start])
    while frontier:
        state = frontier.popleft()
        for transition in successors(state):
            if transition.target.key() not in seen:
                seen[transition.target.key()] = transition.target
                frontier.append(transition.target)
    return list(seen.values())
