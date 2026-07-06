"""Calendar world: schedule meetings around existing conflicts."""

from __future__ import annotations

import random
from typing import List, Optional

from ..core import Environment, StepResult, Task

_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
_EVENT_TITLES = ["offsite", "1:1", "standup", "interview", "training", "all-hands"]
_MEETING_TITLES = ["sync", "review", "planning", "retro", "demo"]

# hour ranges are [start, end) in 24h time
_CANONICAL_EVENTS = [
    {"day": "tuesday", "start": 9, "end": 12, "title": "offsite"},
    {"day": "tuesday", "start": 14, "end": 15, "title": "1:1"},
    {"day": "thursday", "start": 10, "end": 11, "title": "standup"},
]


def _free_start(events: List[dict], day: str, dur: int) -> Optional[int]:
    for start in range(9, 18 - dur):
        end = start + dur
        if not any(e["day"] == day and start < e["end"] and end > e["start"]
                   for e in events):
            return start
    return None


class CalendarEnv(Environment):
    name = "calendar"
    description = "A work calendar (Mon-Fri, 9:00-17:00). Book meetings without conflicts."

    def tasks(self) -> List[Task]:
        return [
            self._task("calendar.sync", _CANONICAL_EVENTS, "tuesday", 1, "sync", None),
            self._task("calendar.review", _CANONICAL_EVENTS, "thursday", 2,
                       "review", "standup"),
        ]

    def generate(self, rng: random.Random) -> Task:
        for _ in range(50):
            day = rng.choice(_DAYS)
            dur = rng.choice([1, 2])
            title = rng.choice(_MEETING_TITLES)
            titles = rng.sample(_EVENT_TITLES, rng.randint(2, 3))
            events = []
            for t in titles:
                start = rng.randint(9, 15)
                events.append({"day": rng.choice(_DAYS), "start": start,
                               "end": start + rng.choice([1, 2]), "title": t})
            cancel = rng.choice(titles) if rng.random() < 0.5 else None
            remaining = [e for e in events if e["title"] != cancel]
            if _free_start(remaining, day, dur) is not None:
                return self._task(f"calendar.gen{rng.randrange(10**6)}",
                                  events, day, dur, title, cancel)
        # extremely unlikely fallback: empty calendar is always solvable
        return self._task(f"calendar.gen{rng.randrange(10**6)}",
                          [], "monday", 1, "sync", None)

    def solve(self, task: Task) -> List[str]:
        s = task.spec
        actions = []
        events = list(s["events"])
        if s["cancel"]:
            actions.append(f"cancel {s['cancel']}")
            events = [e for e in events if e["title"] != s["cancel"]]
        start = _free_start(events, s["day"], s["dur"])
        actions.append(f"book {s['day']} {start} {s['dur']} {s['title']}")
        actions.append("done")
        return actions

    def _task(self, tid: str, events: List[dict], day: str, dur: int,
              title: str, cancel: Optional[str]) -> Task:
        hours = "1 hour" if dur == 1 else f"{dur} hours"
        instruction = (f"Book a {hours} meeting titled '{title}' on "
                       f"{day.capitalize()} that does not overlap any existing event.")
        if cancel:
            instruction += f" Also cancel the '{cancel}'."
        instruction += " Then say done."
        return Task(tid, instruction,
                    spec={"events": [dict(e) for e in events], "day": day,
                          "dur": dur, "title": title, "cancel": cancel})

    def actions_help(self) -> str:
        return ("list <day> | book <day> <hour> <duration_hours> <title> | "
                "cancel <title> | done")

    def reset(self, task: Task) -> str:
        self.task = task
        self.events = [dict(e) for e in task.spec["events"]]
        return "Calendar open. Days: monday-friday, hours 9-17. Try: list monday"

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        if verb == "done":
            return StepResult("calendar closed.", self._score(), True)
        if verb == "list":
            day = rest.strip().lower()
            if day not in _DAYS:
                return StepResult(f"unknown day {rest!r}")
            rows = [f"{e['start']}:00-{e['end']}:00 {e['title']}"
                    for e in self.events if e["day"] == day]
            return StepResult("\n".join(rows) or "(free all day)")
        if verb == "book":
            parts = rest.split(None, 3)
            if len(parts) < 4:
                return StepResult("usage: book <day> <hour> <duration_hours> <title>")
            day, hour, dur, title = parts[0].lower(), parts[1], parts[2], parts[3]
            if day not in _DAYS:
                return StepResult(f"unknown day {parts[0]!r}")
            try:
                start, dur = int(hour), int(dur)
            except ValueError:
                return StepResult("hour and duration must be whole numbers")
            end = start + dur
            if start < 9 or end > 17:
                return StepResult("bookings must fit within 9:00-17:00")
            clash = next((e for e in self.events
                          if e["day"] == day and start < e["end"] and end > e["start"]), None)
            if clash:
                return StepResult(f"conflict with {clash['title']} "
                                  f"({clash['start']}:00-{clash['end']}:00)")
            self.events.append({"day": day, "start": start, "end": end, "title": title})
            return StepResult(f"booked {title} {day} {start}:00-{end}:00")
        if verb == "cancel":
            title = rest.strip().lower()
            before = len(self.events)
            self.events = [e for e in self.events if e["title"].lower() != title]
            return StepResult("cancelled." if len(self.events) < before
                              else f"no event titled {rest!r}")
        return StepResult(f"unknown command: {action!r}. Commands: {self.actions_help()}")

    def _score(self) -> float:
        s = self.task.spec
        booked = any(e["title"].lower() == s["title"] and e["day"] == s["day"]
                     and e["end"] - e["start"] == s["dur"] for e in self.events)
        if not s["cancel"]:
            return 1.0 if booked else 0.0
        cancelled = not any(e["title"] == s["cancel"] for e in self.events)
        return (0.5 * booked) + (0.5 * cancelled)
