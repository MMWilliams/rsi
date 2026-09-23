"""Small tabular Q-learning controller for active CEGIS query allocation."""

from __future__ import annotations

import random
from collections import defaultdict

from dsl import PosError, run
from parse import ParseError, parse

from .cegis_search import solve as cegis_solve
from .common import digest


def state_key(result: dict, query_count: int) -> str:
    """Encode only information available before spending the next oracle query."""
    cost = result.get("cost", {})
    if isinstance(cost, dict):
        signal = int(cost.get("candidate_count", 9999))
    else:
        signal = int(cost)
    cost_bin = min(8, signal // 4)
    return f"q{query_count}:c{cost_bin}"


def _counterexample(program: str, examples: list[list[str]], used: list[list[str]]):
    for pair in examples:
        if pair in used:
            continue
        try:
            output = run(parse(program), pair[0])
        except (ValueError, ParseError, PosError, RecursionError):
            output = None
        if output != pair[1]:
            return pair
    return None


def _synth(task: dict, examples: list[list[str]], config: dict, macros: list[str]) -> dict:
    return cegis_solve({"id": task["id"], "visible": examples}, config,
                       config["budget"], config["max_atoms"], macros, [],
                       synthesize_constants=True)


class TabularQueryPolicy:
    def __init__(self, alpha: float = 0.35, gamma: float = 0.95,
                 query_penalty: float = 0.02, seed: int = 0):
        self.alpha = alpha
        self.gamma = gamma
        self.query_penalty = query_penalty
        self.seed = seed
        self.q = defaultdict(lambda: {"stop": 0.0, "query": 0.0})

    def _update(self, state: str, action: str, target: float) -> None:
        old = self.q[state][action]
        self.q[state][action] = old + self.alpha * (target - old)

    def choose(self, state: str, epsilon: float = 0.0, rng: random.Random | None = None) -> str:
        rng = rng or random.Random(self.seed)
        if rng.random() < epsilon:
            return rng.choice(["stop", "query"])
        values = self.q[state]
        return "query" if values["query"] > values["stop"] else "stop"

    def fit(self, tasks: list[dict], config: dict, macros: list[str],
            episodes: int = 24, max_queries: int = 2) -> dict:
        rng = random.Random(self.seed)
        transitions = 0
        terminals = 0
        for episode in range(episodes):
            epsilon = max(0.03, 0.28 * (1.0 - episode / max(1, episodes - 1)))
            order = list(tasks)
            rng.shuffle(order)
            for task in order:
                examples = list(task["visible"])
                query_count = 0
                pending = None
                for step in range(max_queries + 1):
                    current = _synth(task, examples, config, macros)
                    state = state_key(current, query_count)
                    if pending is not None:
                        prev_state, prev_action = pending
                        self._update(prev_state, prev_action,
                                     self.gamma * max(self.q[state].values()))
                        pending = None
                    action = "stop" if step >= max_queries else self.choose(state, epsilon, rng)
                    if action == "stop":
                        correct = current["program"] == task["reference"]
                        self._update(state, action, float(correct) - self.query_penalty * query_count)
                        terminals += 1
                        break
                    counterexample = _counterexample(current["program"], task["hidden"], examples)
                    query_count += 1
                    if counterexample is None:
                        correct = current["program"] == task["reference"]
                        self._update(state, action, float(correct) - self.query_penalty * query_count)
                        terminals += 1
                        break
                    examples.append(counterexample)
                    pending = (state, action)
                    transitions += 1
        return {"episodes": episodes, "states": len(self.q), "transitions": transitions,
                "terminals": terminals, "q_sha256": digest(dict(self.q))}

    def to_dict(self) -> dict:
        return {state: dict(values) for state, values in sorted(self.q.items())}


def solve(task: dict, policy: TabularQueryPolicy, config: dict, macros: list[str],
          max_queries: int = 2) -> dict:
    examples = list(task["visible"])
    trace = []
    query_count = 0
    for step in range(max_queries + 1):
        current = _synth(task, examples, config, macros)
        state = state_key(current, query_count)
        action = "stop" if step >= max_queries else policy.choose(state)
        trace.append({"state": state, "action": action, "cost": current.get("cost")})
        if action == "stop":
            break
        counterexample = _counterexample(current["program"], task["hidden"], examples)
        query_count += 1
        if counterexample is None:
            break
        examples.append(counterexample)
    result = dict(current)
    result.update({"queries": query_count, "examples_used": len(examples), "trace": trace,
                   "rl_policy_sha256": digest(policy.to_dict())})
    result["replay_sha256"] = digest(result)
    return result
