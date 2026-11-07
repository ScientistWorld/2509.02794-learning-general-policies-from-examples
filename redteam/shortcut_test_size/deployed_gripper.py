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

    def is_goal(self) -> bool:
        return self.balls_at_a == 0 and self.carried == 0

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


def successors(state: State) -> list[Transition]:
    out: list[Transition] = []
    if state.at_a:
        if state.balls_at_a > 0 and state.carried < state.capacity:
            out.append(
                Transition(
                    state,
                    State(
                        state.balls_at_a - 1,
                        state.carried + 1,
                        True,
                        state.total_balls,
                        state.capacity,
                    ),
                    "pick",
                )
            )
        if state.carried > 0:
            out.append(
                Transition(
                    state,
                    State(state.balls_at_a, state.carried, False, state.total_balls, state.capacity),
                    "move_to_b",
                )
            )
        return out

    if state.carried > 0:
        out.append(
            Transition(
                state,
                State(state.balls_at_a, state.carried - 1, False, state.total_balls, state.capacity),
                "drop",
            )
        )
    if state.carried == 0 and state.balls_at_a > 0:
        out.append(
            Transition(
                state,
                State(state.balls_at_a, 0, True, state.total_balls, state.capacity),
                "move_to_a",
            )
        )
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
    plan: list[Transition] = []
    seen: set[tuple[int, int, bool, int, int]] = set()
    while not state.is_goal():
        if state.key() in seen:
            raise RuntimeError(f"planner looped on {state}")
        seen.add(state.key())
        if state.at_a and state.balls_at_a > 0 and state.carried < state.capacity:
            chosen = next(t for t in successors(state) if t.action == "pick")
        elif state.at_a and state.carried > 0:
            chosen = next(t for t in successors(state) if t.action == "move_to_b")
        elif (not state.at_a) and state.carried > 0:
            chosen = next(t for t in successors(state) if t.action == "drop")
        elif (not state.at_a) and state.balls_at_a > 0:
            chosen = next(t for t in successors(state) if t.action == "move_to_a")
        else:
            raise RuntimeError(f"no plan action from {state}")
        plan.append(chosen)
        state = chosen.target
    return plan


def feature_pool(extra_distractors: int = 80) -> list[Feature]:
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
    return [Instance(f"train_{n}", n) for n in range(1, 6)]


def test_instances() -> list[Instance]:
    return [Instance("shortcut_empty_0", 0), Instance("shortcut_empty_1", 0)]


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


def action_plan_baseline(instance: Instance) -> list[str]:
    return [t.action for t in planner(instance)]


def alive_states(instance: Instance) -> Iterable[State]:
    for state in all_states(instance):
        if not state.is_goal():
            yield state
