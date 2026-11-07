"""Domain-independent pieces of the feature-based policy language.

A feature maps a state to a non-negative integer (numerical) or a Boolean.
These helpers describe how a feature changes across a transition, which is
what policy rules talk about. Shared by every domain module in `data/`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Transition:
    source: Any
    target: Any
    action: str


@dataclass(frozen=True)
class Feature:
    name: str
    kind: str
    complexity: int
    value_fn: Callable[[Any], int | bool]

    def value(self, state) -> int | bool:
        return self.value_fn(state)

    def positive(self, state) -> bool:
        value = self.value(state)
        return bool(value) if self.kind == "bool" else int(value) > 0


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


def valuation(feature: Feature, state) -> str:
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
