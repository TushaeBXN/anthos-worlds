"""Warehouse world: a robot on a 5x5 grid moving crates between cells.

Columns are A-E (west to east), rows 1-5 (north to south); "A1" is the
northwest corner.
"""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

from ..core import Environment, StepResult, Task

_COLS = "ABCDE"
_CELLS = [f"{c}{r}" for c in _COLS for r in range(1, 6)]


def _coords(cell: str) -> Tuple[int, int]:
    return _COLS.index(cell[0]), int(cell[1]) - 1


def _cell(col: int, row: int) -> str:
    return f"{_COLS[col]}{row + 1}"


def _walk(a: str, b: str) -> List[str]:
    (ac, ar), (bc, br) = _coords(a), _coords(b)
    moves = ["east"] * (bc - ac) if bc >= ac else ["west"] * (ac - bc)
    moves += ["south"] * (br - ar) if br >= ar else ["north"] * (ar - br)
    return moves


class WarehouseEnv(Environment):
    name = "warehouse"
    description = ("A 5x5 warehouse grid (A1 northwest to E5 southeast) with a "
                   "robot that can carry one crate at a time.")

    def tasks(self) -> List[Task]:
        return [
            self._task("warehouse.single", "C3", {"A3": "D1"}, max_steps=25),
            self._task("warehouse.swap-lane", "C3", {"B2": "B5", "E5": "E1"},
                       max_steps=40),
        ]

    def generate(self, rng: random.Random) -> Task:
        robot = rng.choice(_CELLS)
        k = rng.choice([1, 2])
        starts = rng.sample(_CELLS, k)
        goals = rng.sample([c for c in _CELLS if c not in starts], k)
        crates = dict(zip(starts, goals))
        return self._task(f"warehouse.gen{rng.randrange(10**6)}", robot, crates,
                          max_steps=30 * k)

    def solve(self, task: Task) -> List[str]:
        s = task.spec
        actions: List[str] = []
        at = s["robot"]
        for start in sorted(s["crates"]):
            goal = s["crates"][start]
            actions += _walk(at, start) + ["grab"] + _walk(start, goal) + ["drop"]
            at = goal
        return actions

    def _task(self, tid: str, robot: str, crates: Dict[str, str],
              max_steps: int) -> Task:
        moves = " and ".join(f"the crate at {src} to {dst}"
                             for src, dst in sorted(crates.items()))
        return Task(tid, f"Move {moves}.", max_steps=max_steps,
                    spec={"robot": robot, "crates": dict(crates)})

    def actions_help(self) -> str:
        return "north | south | east | west | grab | drop | where"

    def reset(self, task: Task) -> str:
        self.task = task
        self.pos = _coords(task.spec["robot"])
        self.holding = False
        self.crates = {src: True for src in task.spec["crates"]}
        return (f"Robot at {_cell(*self.pos)}. "
                f"Crates at: {', '.join(sorted(self.crates))}.")

    def step(self, action: str) -> StepResult:
        verb, _ = self.parse(action)
        moves = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
        if verb in moves:
            dc, dr = moves[verb]
            col, row = self.pos[0] + dc, self.pos[1] + dr
            if not (0 <= col < 5 and 0 <= row < 5):
                return StepResult("bump — a wall.")
            self.pos = (col, row)
            return StepResult(f"robot at {_cell(col, row)}.")
        if verb == "grab":
            here = _cell(*self.pos)
            if self.holding:
                return StepResult("already carrying a crate.")
            if not self.crates.get(here):
                return StepResult("no crate here.")
            del self.crates[here]
            self.holding = True
            return StepResult(f"grabbed the crate at {here}.")
        if verb == "drop":
            here = _cell(*self.pos)
            if not self.holding:
                return StepResult("not carrying anything.")
            if self.crates.get(here):
                return StepResult("there is already a crate here.")
            self.crates[here] = True
            self.holding = False
            score = self._score()
            if score >= 1.0:
                return StepResult(f"dropped at {here}. All crates in place!", score, True)
            return StepResult(f"dropped at {here}.")
        if verb == "where":
            return StepResult(f"robot at {_cell(*self.pos)}; "
                              f"crates at {', '.join(sorted(self.crates)) or '(none)'}; "
                              f"carrying: {self.holding}")
        return StepResult(f"unknown command: {action!r}. Commands: {self.actions_help()}")

    def _score(self) -> float:
        goals = set(self.task.spec["crates"].values())
        placed = sum(1 for cell in goals if self.crates.get(cell))
        return placed / len(goals) if goals else 0.0
