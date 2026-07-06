"""Warehouse world: a robot on a 5x5 grid moving crates between cells.

Columns are A-E (west to east), rows 1-5 (north to south); "A1" is the
northwest corner.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from ..core import Environment, StepResult, Task

_COLS = "ABCDE"


def _cell(col: int, row: int) -> str:
    return f"{_COLS[col]}{row + 1}"


class WarehouseEnv(Environment):
    name = "warehouse"
    description = ("A 5x5 warehouse grid (A1 northwest to E5 southeast) with a "
                   "robot that can carry one crate at a time.")

    def tasks(self) -> List[Task]:
        return [
            Task("warehouse.single",
                 "Move the crate at A3 to D1.", max_steps=25),
            Task("warehouse.swap-lane",
                 "Move the crate at B2 to B5 and the crate at E5 to E1.",
                 max_steps=40),
        ]

    def actions_help(self) -> str:
        return "north | south | east | west | grab | drop | where"

    def reset(self, task: Task) -> str:
        self.task = task
        self.pos: Tuple[int, int] = (2, 2)  # C3
        self.holding: bool = False
        if task.id == "warehouse.single":
            self.crates: Dict[str, bool] = {"A3": True}
        else:
            self.crates = {"B2": True, "E5": True}
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
        goals = {"warehouse.single": {"D1"}, "warehouse.swap-lane": {"B5", "E1"}}
        want = goals.get(self.task.id, set())
        placed = sum(1 for cell in want if self.crates.get(cell))
        return placed / len(want) if want else 0.0
