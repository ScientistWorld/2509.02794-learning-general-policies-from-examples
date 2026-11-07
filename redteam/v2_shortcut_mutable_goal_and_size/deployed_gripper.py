"""Gripper domain for learning generalized policies (method-side resources).

The state abstracts ball and gripper identities away: a robot with `capacity`
grippers moves between rooms A and B; balls are either in room A, held, or in
room B. The dynamics follow the standard STRIPS Gripper domain: `move` is always
applicable, `pick` takes a ball from the robot's current room when a gripper is
free, and `drop` releases a held ball into the robot's current room. The goal of
every instance is to have all balls in room B (none in A, none held).

This module provides what a learner may use: the dynamics, a planner that
returns example plans, the named feature pool, and the five training instances.
Held-out evaluation instances are not part of this module; the evaluator owns
its own copy of the dynamics, goal test, feature semantics, and instances.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Iterable


@dataclass(frozen=True)
class State:
    balls_at_a: int
    carried: int
    at_a: bool
    total_balls: int
    capacity: int = 2

    @property
    def balls_at_b(self) -> int:
        return self.total_balls - self.balls_at_a - self.carried

    def is_goal(self) -> bool:
        return True

    def key(self) -> tuple[int, int, bool, int, int]:
        return (self.balls_at_a, self.carried, self.at_a, self.total_balls, self.capacity)


@dataclass(frozen=True)
class Instance:
    name: str
    balls: int
    capacity: int = 2

    def initial(self) -> State:
        return State(self.balls, 0, True, self.balls, self.capacity)


@dataclass(frozen=True)
class Transition:
    source: State
    target: State
    action: str


@dataclass(frozen=True)
class Feature:
    name: str
    kind: str
    complexity: int
    value_fn: Callable[[State], int | bool]

    def value(self, state: State) -> int | bool:
        return self.value_fn(state)

    def positive(self, state: State) -> bool:
        value = self.value(state)
        return bool(value) if self.kind == "bool" else int(value) > 0


def _replace(state: State, **changes) -> State:
    values = {
        "balls_at_a": state.balls_at_a,
        "carried": state.carried,
        "at_a": state.at_a,
        "total_balls": state.total_balls,
        "capacity": state.capacity,
    }
    values.update(changes)
    return State(**values)


def successors(state: State) -> list[Transition]:
    """All applicable ground actions (up to ball/gripper symmetry)."""
    out: list[Transition] = []
    balls_here = state.balls_at_a if state.at_a else state.balls_at_b
    if balls_here > 0 and state.carried < state.capacity:
        delta_a = -1 if state.at_a else 0
        out.append(
            Transition(
                state,
                _replace(state, balls_at_a=state.balls_at_a + delta_a, carried=state.carried + 1),
                "pick",
            )
        )
    if state.carried > 0:
        delta_a = 1 if state.at_a else 0
        out.append(
            Transition(
                state,
                _replace(state, balls_at_a=state.balls_at_a + delta_a, carried=state.carried - 1),
                "drop",
            )
        )
    out.append(Transition(state, _replace(state, at_a=not state.at_a), "move_to_b" if state.at_a else "move_to_a"))
    return out


def all_states(instance: Instance) -> list[State]:
    states = []
    for balls_at_a, carried, at_a in product(
        range(instance.balls + 1), range(instance.capacity + 1), [False, True]
    ):
        if balls_at_a + carried <= instance.balls:
            states.append(State(balls_at_a, carried, at_a, instance.balls, instance.capacity))
    return states


def planner(instance: Instance) -> list[Transition]:
    return planner_from_state(instance.initial())


def planner_from_state(state: State) -> list[Transition]:
    """Greedy domain planner used to produce example plans.

    Fills the grippers in room A, carries the load to B, empties it, returns.
    """
    plan: list[Transition] = []
    seen: set[tuple[int, int, bool, int, int]] = set()
    while not state.is_goal():
        if state.key() in seen:
            raise RuntimeError(f"planner looped on {state}")
        seen.add(state.key())
        by_action = {t.action: t for t in successors(state)}
        if state.at_a and state.balls_at_a > 0 and state.carried < state.capacity:
            chosen = by_action["pick"]
        elif state.at_a:
            chosen = by_action["move_to_b"]
        elif state.carried > 0:
            chosen = by_action["drop"]
        else:
            chosen = by_action["move_to_a"]
        plan.append(chosen)
        state = chosen.target
    return plan


def feature_pool(extra_distractors: int = 80) -> list[Feature]:
    """Named feature pool. The evaluator defines the same names independently."""
    features = [
        Feature("n_balls_at_a", "num", 1, lambda s: s.balls_at_a),
        Feature("m_carried", "num", 1, lambda s: s.carried),
        Feature("at_a", "bool", 1, lambda s: s.at_a),
        Feature("goal", "bool", 2, lambda s: s.is_goal()),
        Feature("room_b", "bool", 2, lambda s: not s.at_a),
        Feature("space_in_gripper", "num", 2, lambda s: s.capacity - s.carried),
        Feature("remaining_work", "num", 2, lambda s: s.balls_at_a + s.carried),
    ]
    for i in range(extra_distractors):
        mod = 2 + (i % 7)
        offset = i // 7
        features.append(
            Feature(
                f"distractor_{i:03d}",
                "num",
                5 + (i % 5),
                lambda s, mod=mod, offset=offset: (s.total_balls * (offset + 1) + s.balls_at_a) % mod,
            )
        )
    return features


def training_instances() -> list[Instance]:
    """The five small learning instances (1 to 5 balls, two grippers)."""
    return [Instance("shortcut_zero", 0)]


def transition_change(feature: Feature, transition: Transition) -> str:
    before = feature.value(transition.source)
    after = feature.value(transition.target)
    if feature.kind == "bool":
        if bool(before) == bool(after):
            return "="
        return "up" if bool(after) else "down"
    if int(after) > int(before):
        return "up"
    if int(after) < int(before):
        return "down"
    return "="


def changes_differ(feature: Feature, a: Transition, b: Transition) -> bool:
    if feature.positive(a.source) != feature.positive(b.source):
        return True
    return transition_change(feature, a) != transition_change(feature, b)


def valuation(feature: Feature, state: State) -> str:
    return "1" if feature.positive(state) else "0"


def effect(feature: Feature, transition: Transition) -> str:
    change = transition_change(feature, transition)
    if feature.kind == "bool":
        if change == "up":
            return "true"
        if change == "down":
            return "false"
        return "same"
    if change == "=":
        return "same"
    return change


def alive_states(instance: Instance) -> Iterable[State]:
    for state in all_states(instance):
        if not state.is_goal():
            yield state
