"""Learners and fixed artifacts for the hardening audit (iteration 12).

Every function writes one method directory with `policy.json` (Gripper) and
`childsnack_policy.json` (Childsnack). A variant changes one experiment and
keeps the reference's artifact for the other, so its rank isolates that change.

Usage: python -m redteam.hardening_v3.variants <case> <out_dir> [<reference_dir>]
"""
from __future__ import annotations

import json
import shutil
import sys
from collections import deque
from pathlib import Path

from data import childsnack, gripper
from method import genex as G

SAVED = Path("redteam")


def _write(out: Path, name: str, payload: dict) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _learn(domain, out: Path, name: str) -> None:
    policy, stats = G.learn_policy(domain)
    G.policy_to_json(policy, stats, out / name)


def _copy_reference(ref: Path, out: Path, which: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    shutil.copy(ref / which, out / which)


# ---------------------------------------------------------------------------
# Reference
# ---------------------------------------------------------------------------


def reference(out: Path, ref: Path | None) -> None:
    _learn(gripper, out, "policy.json")
    _learn(childsnack, out, "childsnack_policy.json")


# ---------------------------------------------------------------------------
# Gripper variants (Childsnack artifact = reference)
# ---------------------------------------------------------------------------


def gripper_better_refinement(out: Path, ref: Path) -> None:
    """Learned: refine the reference with planner labels on all training states (red-team v2 learner)."""
    from redteam.audit_v2.refine import refine

    policy = refine(json.loads((ref / "policy.json").read_text()))
    _write(out, "policy.json", policy)
    _copy_reference(ref, out, "childsnack_policy.json")


def _saved_gripper(case: str):
    def build(out: Path, ref: Path) -> None:
        _write(out, "policy.json", json.loads((SAVED / case / "policy.json").read_text()))
        _copy_reference(ref, out, "childsnack_policy.json")

    build.__doc__ = f"Saved red-team artifact {case}/policy.json"
    return build


def gripper_weaker_lazy_one_ball(out: Path, ref: Path) -> None:
    """The reference with a pickup only when holding nothing: one ball per trip."""
    policy = json.loads((ref / "policy.json").read_text())
    for rule in policy["rules"]:
        if rule.get("source_action") == "pick":
            rule["condition"] = [["m_carried", "0"]]
    _write(out, "policy.json", policy)
    _copy_reference(ref, out, "childsnack_policy.json")


# ---------------------------------------------------------------------------
# Childsnack variants (Gripper artifact = reference)
# ---------------------------------------------------------------------------


def childsnack_better_all_states(out: Path, ref: Path) -> None:
    """Learned: WRAPPER whose test on Q' and Q starts from every reachable alive state.

    Same GENEX, projection and simplification. The WRAPPER test (Alg. 2,
    lines 7-8) checks that the policy is closed and safe from every reachable
    non-dead-end state of each training instance, not only from its initial
    state, so the learned rules must cope with situations off the example
    plans (sandwiches already made or on the tray, tray at a table). Only the
    ten training instances are used.
    """
    original = G.verify_policy
    alive_by_instance: dict[str, list] = {}

    def _alive_states(instance) -> list:
        if instance.name not in alive_by_instance:
            alive_by_instance[instance.name] = sorted(
                (s for s in childsnack.all_states(instance) if not s.is_goal() and not childsnack.is_dead_end(s)),
                key=lambda s: s.key(),
            )
        return alive_by_instance[instance.name]

    def _verify_from(policy, starts, domain) -> dict:
        """One multi-source exploration of the policy graph from every start state.

        Equivalent to verifying from each start separately (closed and safe on
        the union of reachable states; the union graph is acyclic iff every
        per-start subgraph is), but linear rather than quadratic in the number
        of states.
        """
        states = {s.key(): s for s in starts}
        frontier = deque(states.values())
        graph: dict[tuple, list[tuple]] = {}
        while frontier:
            state = frontier.popleft()
            if state.is_goal():
                graph[state.key()] = []
                continue
            candidates = G.policy_successors(policy, state, domain)
            if not candidates:
                return {"solved": False, "reason": "undefined", "state": state}
            graph[state.key()] = []
            for transition in candidates:
                target = transition.target
                if not target.is_goal() and G._is_dead_end(target, domain):
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

    def verify_from_all_states(policy, instance, domain=G.gripper_domain):
        if domain is not childsnack:
            return original(policy, instance, domain)
        result = original(policy, instance, domain)
        if not result["solved"]:
            return result
        return _verify_from(policy, _alive_states(instance), domain)

    G.verify_policy = verify_from_all_states
    try:
        _learn(childsnack, out, "childsnack_policy.json")
    finally:
        G.verify_policy = original
    _copy_reference(ref, out, "policy.json")


def childsnack_weaker_no_simplification(out: Path, ref: Path) -> None:
    """Learned: the reference pipeline without the optional simplification (line 6)."""
    original = G.simplify_policy
    G.simplify_policy = lambda policy, x_neg, q_prime=None, domain=None: policy
    try:
        _learn(childsnack, out, "childsnack_policy.json")
    finally:
        G.simplify_policy = original
    _copy_reference(ref, out, "policy.json")


def childsnack_weaker_wasteful_make(out: Path, ref: Path) -> None:
    """The reference with the gluten-free guard on regular sandwiches dropped."""
    policy = json.loads((ref / "childsnack_policy.json").read_text())
    for rule in policy["rules"]:
        if rule.get("source_action", "").startswith("make_sandwich[") and rule["condition"]:
            rule["condition"] = [c for c in rule["condition"] if c[0] != "gf_bread_at_kitchen"]
    _write(out, "childsnack_policy.json", policy)
    _copy_reference(ref, out, "policy.json")


# ---------------------------------------------------------------------------
# Shortcuts
# ---------------------------------------------------------------------------


def shortcut_missing_childsnack(out: Path, ref: Path) -> None:
    """Submits only the Gripper reference artifact."""
    _copy_reference(ref, out, "policy.json")


def shortcut_childsnack_admit_all(out: Path, ref: Path) -> None:
    """Childsnack: zero features, one unconditional rule (implicit planner)."""
    _write(out, "childsnack_policy.json", {"selected_features": [], "rules": [{"condition": [], "effects": []}]})
    _copy_reference(ref, out, "policy.json")


def shortcut_childsnack_forged(out: Path, ref: Path) -> None:
    """Childsnack: empty rules plus forged coverage, quality and width fields."""
    _write(out, "childsnack_policy.json", {
        "selected_features": ["served_children"], "rules": [],
        "heldout_coverage": 1.0, "policy_quality": 1.0, "max_effective_width": 0.0,
        "stats": {"solved": True, "coverage": 1.0},
    })
    _copy_reference(ref, out, "policy.json")


def shortcut_childsnack_unknown_feature(out: Path, ref: Path) -> None:
    """Childsnack: an invented 'distance_to_goal' feature that decreases on every rule."""
    _write(out, "childsnack_policy.json", {
        "selected_features": ["distance_to_goal"],
        "rules": [{"condition": [["distance_to_goal", "1"]], "effects": [["distance_to_goal", "down"]]}],
    })
    _copy_reference(ref, out, "policy.json")


def shortcut_childsnack_unstratified(out: Path, ref: Path) -> None:
    """Childsnack: broad rules that solve by executor luck but are not structurally terminating."""
    _write(out, "childsnack_policy.json", {
        "selected_features": ["sandwiches_on_tray", "tray_at_kitchen", "served_children"],
        "rules": [
            {"condition": [], "effects": [["sandwiches_on_tray", "up"]]},
            {"condition": [], "effects": [["sandwiches_on_tray", "down"], ["served_children", "up"]]},
            {"condition": [], "effects": [["tray_at_kitchen", "false"]]},
            {"condition": [], "effects": [["tray_at_kitchen", "true"]]},
        ],
    })
    _copy_reference(ref, out, "policy.json")


CASES = {
    "reference": reference,
    "gripper_better_refinement": gripper_better_refinement,
    "gripper_weaker_lazy_one_ball": gripper_weaker_lazy_one_ball,
    "gripper_weaker_redundant_feature": _saved_gripper("v2_weaker_redundant_feature"),
    "gripper_weaker_no_pick": _saved_gripper("v2_weaker_no_pick"),
    "childsnack_better_all_states": childsnack_better_all_states,
    "childsnack_weaker_no_simplification": childsnack_weaker_no_simplification,
    "childsnack_weaker_wasteful_make": childsnack_weaker_wasteful_make,
    "shortcut_missing_childsnack": shortcut_missing_childsnack,
    "shortcut_childsnack_admit_all": shortcut_childsnack_admit_all,
    "shortcut_childsnack_forged": shortcut_childsnack_forged,
    "shortcut_childsnack_unknown_feature": shortcut_childsnack_unknown_feature,
    "shortcut_childsnack_unstratified": shortcut_childsnack_unstratified,
    "shortcut_gripper_implicit_planner": _saved_gripper("v2_shortcut_implicit_planner"),
    "shortcut_gripper_undercount_features": _saved_gripper("v2_shortcut_undercount_features"),
    "shortcut_gripper_unknown_feature": _saved_gripper("v2_shortcut_unknown_feature"),
    "shortcut_gripper_impossible_values": _saved_gripper("v2_shortcut_impossible_values"),
    "shortcut_gripper_handwritten_optimal": _saved_gripper("v2_shortcut_handwritten_optimal"),
}


def main() -> None:
    case, out = sys.argv[1], Path(sys.argv[2])
    ref = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    CASES[case](out, ref)


if __name__ == "__main__":
    main()
