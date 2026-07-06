"""Quest world: a small text adventure — rooms, items, and a locked chest."""

from __future__ import annotations

from typing import Dict, List

from ..core import Environment, StepResult, Task

_ROOMS: Dict[str, Dict] = {
    "hall": {"exits": {"down": "cellar", "up": "attic"},
             "detail": "A dusty hall. Stairs lead up and down.", "items": []},
    "cellar": {"exits": {"up": "hall"},
               "detail": "A damp cellar. Something glints on the floor.",
               "items": ["key", "rope"]},
    "attic": {"exits": {"down": "hall"},
              "detail": "A cramped attic holding a locked chest.", "items": []},
}


class QuestEnv(Environment):
    name = "quest"
    description = "A text adventure. Explore rooms, collect items, reach the goal."

    def tasks(self) -> List[Task]:
        return [
            Task("quest.chest",
                 "Find the key hidden somewhere in the house and use it to open "
                 "the chest in the attic."),
            Task("quest.rope",
                 "Retrieve the rope from wherever it is and bring it back to the "
                 "hall, then say done.", max_steps=15),
        ]

    def actions_help(self) -> str:
        return "look | go <direction> | take <item> | use <item> | inventory | done"

    def reset(self, task: Task) -> str:
        self.task = task
        self.rooms = {k: {**v, "items": list(v["items"])} for k, v in _ROOMS.items()}
        self.at = "hall"
        self.bag: List[str] = []
        self.chest_open = False
        return f"You are in the hall. {self.rooms['hall']['detail']}"

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        room = self.rooms[self.at]
        if verb == "done":
            return StepResult("you stop.", self._score(), True)
        if verb == "look":
            items = f" You see: {', '.join(room['items'])}." if room["items"] else ""
            exits = ", ".join(room["exits"])
            return StepResult(f"{room['detail']}{items} Exits: {exits}.")
        if verb == "go":
            dest = room["exits"].get(rest.strip().lower())
            if not dest:
                return StepResult(f"you can't go {rest!r} from here.")
            self.at = dest
            return StepResult(f"You are in the {dest}. {self.rooms[dest]['detail']}")
        if verb == "take":
            item = rest.strip().lower()
            if item in room["items"]:
                room["items"].remove(item)
                self.bag.append(item)
                return StepResult(f"taken: {item}")
            return StepResult(f"no {item!r} here.")
        if verb == "use":
            item = rest.strip().lower()
            if item not in self.bag:
                return StepResult(f"you aren't carrying {item!r}.")
            if item == "key" and self.at == "attic":
                self.chest_open = True
                return StepResult("The chest creaks open. Gold!", self._score(), True)
            return StepResult(f"nothing happens when you use the {item} here.")
        if verb == "inventory":
            return StepResult(f"carrying: {', '.join(self.bag) or '(nothing)'}")
        return StepResult(f"unknown command: {action!r}. Commands: {self.actions_help()}")

    def _score(self) -> float:
        if self.task.id == "quest.chest":
            return 1.0 if self.chest_open else 0.0
        if self.task.id == "quest.rope":
            return 1.0 if "rope" in self.bag and self.at == "hall" else 0.0
        return 0.0
