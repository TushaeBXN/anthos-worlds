"""Quest world: a small text adventure — rooms, items, and a locked chest."""

from __future__ import annotations

import random
from typing import Dict, List

from ..core import Environment, StepResult, Task

_ROOMS: Dict[str, Dict] = {
    "hall": {"exits": {"down": "cellar", "up": "attic"},
             "detail": "A dusty hall. Stairs lead up and down."},
    "cellar": {"exits": {"up": "hall"},
               "detail": "A damp cellar. Something might be hidden here."},
    "attic": {"exits": {"down": "hall"},
              "detail": "A cramped attic holding a locked chest."},
}

# shortest routes between rooms (the house is tiny; hall is the hub)
_PATHS = {
    ("hall", "cellar"): ["go down"], ("cellar", "hall"): ["go up"],
    ("hall", "attic"): ["go up"], ("attic", "hall"): ["go down"],
    ("cellar", "attic"): ["go up", "go up"], ("attic", "cellar"): ["go down", "go down"],
}

_FETCH_ITEMS = ["rope", "lantern", "coin", "map"]


def _path(a: str, b: str) -> List[str]:
    return [] if a == b else _PATHS[(a, b)]


class QuestEnv(Environment):
    name = "quest"
    description = "A text adventure. Explore rooms, collect items, reach the goal."

    def tasks(self) -> List[Task]:
        return [
            self._chest_task("quest.chest", "cellar"),
            self._fetch_task("quest.rope", "rope", "cellar"),
        ]

    def generate(self, rng: random.Random) -> Task:
        tid = f"quest.gen{rng.randrange(10**6)}"
        if rng.random() < 0.5:
            return self._chest_task(tid, rng.choice(["cellar", "hall"]))
        return self._fetch_task(tid, rng.choice(_FETCH_ITEMS),
                                rng.choice(["cellar", "attic"]))

    def solve(self, task: Task) -> List[str]:
        s = task.spec
        if s["kind"] == "chest":
            return (_path("hall", s["key_room"]) + ["take key"]
                    + _path(s["key_room"], "attic") + ["use key"])
        return (_path("hall", s["room"]) + [f"take {s['item']}"]
                + _path(s["room"], "hall") + ["done"])

    def _chest_task(self, tid: str, key_room: str) -> Task:
        return Task(tid, "Find the key hidden somewhere in the house and use it "
                         "to open the chest in the attic.",
                    spec={"kind": "chest", "key_room": key_room})

    def _fetch_task(self, tid: str, item: str, room: str) -> Task:
        return Task(tid, f"Retrieve the {item} from wherever it is and bring it "
                         f"back to the hall, then say done.", max_steps=15,
                    spec={"kind": "fetch", "item": item, "room": room})

    def actions_help(self) -> str:
        return "look | go <direction> | take <item> | use <item> | inventory | done"

    def reset(self, task: Task) -> str:
        self.task = task
        self.rooms = {k: {**v, "items": []} for k, v in _ROOMS.items()}
        s = task.spec
        if s["kind"] == "chest":
            self.rooms[s["key_room"]]["items"].append("key")
        else:
            self.rooms[s["room"]]["items"].append(s["item"])
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
        s = self.task.spec
        if s["kind"] == "chest":
            return 1.0 if self.chest_open else 0.0
        return 1.0 if s["item"] in self.bag and self.at == "hall" else 0.0
