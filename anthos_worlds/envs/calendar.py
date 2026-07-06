"""Calendar world: schedule meetings around existing conflicts."""

from __future__ import annotations

from typing import List

from ..core import Environment, StepResult, Task

_DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday"]
# hour ranges are [start, end) in 24h time
_EXISTING = [
    {"day": "tuesday", "start": 9, "end": 12, "title": "offsite"},
    {"day": "tuesday", "start": 14, "end": 15, "title": "1:1"},
    {"day": "thursday", "start": 10, "end": 11, "title": "standup"},
]


class CalendarEnv(Environment):
    name = "calendar"
    description = "A work calendar (Mon-Fri, 9:00-17:00). Book meetings without conflicts."

    def tasks(self) -> List[Task]:
        return [
            Task("calendar.sync",
                 "Book a 1-hour meeting titled 'sync' on Tuesday that does not "
                 "overlap any existing event. Then say done."),
            Task("calendar.review",
                 "Book a 2-hour meeting titled 'review' on Thursday with no "
                 "conflicts, and cancel the 'standup'. Then say done."),
        ]

    def actions_help(self) -> str:
        return ("list <day> | book <day> <hour> <duration_hours> <title> | "
                "cancel <title> | done")

    def reset(self, task: Task) -> str:
        self.task = task
        self.events = [dict(e) for e in _EXISTING]
        return "Calendar open. Days: monday-friday, hours 9-17. Try: list tuesday"

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

    def _booked(self, title: str, day: str, dur: int) -> bool:
        return any(e["title"].lower() == title and e["day"] == day
                   and e["end"] - e["start"] == dur for e in self.events)

    def _score(self) -> float:
        if self.task.id == "calendar.sync":
            return 1.0 if self._booked("sync", "tuesday", 1) else 0.0
        if self.task.id == "calendar.review":
            booked = self._booked("review", "thursday", 2)
            cancelled = not any(e["title"] == "standup" for e in self.events)
            return (0.5 * booked) + (0.5 * cancelled)
        return 0.0
