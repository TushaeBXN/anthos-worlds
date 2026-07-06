"""Core types: everything in AnthosWorlds is text in, text out.

An Environment exposes tasks; ``reset(task)`` returns the first observation
and ``step(action)`` consumes one plain-text command. Rewards land in [0, 1],
usually on the final step, so any LLM (or scripted policy) can play without
special tooling.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class Task:
    id: str
    instruction: str
    max_steps: int = 20
    spec: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    observation: str
    reward: float = 0.0
    done: bool = False


@dataclass
class Step:
    action: str
    observation: str


@dataclass
class Episode:
    env: str
    task: Task
    first_observation: str
    steps: List[Step] = field(default_factory=list)
    reward: float = 0.0

    @property
    def success(self) -> bool:
        return self.reward >= 1.0


class Environment(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def tasks(self) -> List[Task]:
        """The canonical, deterministic tasks this environment ships with."""

    @abstractmethod
    def generate(self, rng: random.Random) -> Task:
        """Sample a procedurally generated task variant. Deterministic for a
        given rng state, and always solvable."""

    @abstractmethod
    def solve(self, task: Task) -> List[str]:
        """Return an action sequence that completes ``task`` with reward 1.0.
        Powers the oracle agent and CI solvability checks."""

    @abstractmethod
    def actions_help(self) -> str:
        """One line per available command, shown to the agent."""

    @abstractmethod
    def reset(self, task: Task) -> str:
        """Start ``task`` and return the first observation."""

    @abstractmethod
    def step(self, action: str) -> StepResult:
        """Apply one text command."""

    @staticmethod
    def parse(action: str) -> tuple:
        """Split ``action`` into (verb, rest). Verbs are case-insensitive."""
        action = action.strip()
        if not action:
            return "", ""
        parts = action.split(None, 1)
        return parts[0].lower(), parts[1] if len(parts) > 1 else ""
