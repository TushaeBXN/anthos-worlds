"""Helpdesk world: route support tickets to the right team."""

from __future__ import annotations

from typing import Dict, List

from ..core import Environment, StepResult, Task

_TICKETS = [
    {"id": "t1", "subject": "Charged twice this month",
     "body": "My card shows two subscription charges for May.", "team": "billing"},
    {"id": "t2", "subject": "App crashes on launch",
     "body": "Since the last update the app closes immediately on my phone.",
     "team": "tech"},
    {"id": "t3", "subject": "Change my account email",
     "body": "I need to update the login email on my profile.", "team": "account"},
    {"id": "t4", "subject": "Refund for annual plan",
     "body": "I cancelled within the trial window, please refund the invoice.",
     "team": "billing"},
]

_TEAMS = ("billing", "tech", "account")


class HelpdeskEnv(Environment):
    name = "helpdesk"
    description = ("A support queue. Read tickets and route each to the right "
                   "team: billing, tech, or account.")

    def tasks(self) -> List[Task]:
        return [
            Task("helpdesk.triage",
                 "Assign every open ticket to the correct team (billing, tech, "
                 "or account) based on its content. Then say done."),
            Task("helpdesk.billing-sweep",
                 "Assign only the billing-related tickets to the billing team, "
                 "touch nothing else, then say done."),
        ]

    def actions_help(self) -> str:
        return "list | read <id> | assign <id> <team> | done"

    def reset(self, task: Task) -> str:
        self.task = task
        self.assigned: Dict[str, str] = {}
        return f"Queue: {len(_TICKETS)} open tickets. Teams: {', '.join(_TEAMS)}. Try: list"

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        if verb == "done":
            return StepResult("queue closed.", self._score(), True)
        if verb == "list":
            rows = [f"[{t['id']}] {t['subject']}"
                    f"{' -> ' + self.assigned[t['id']] if t['id'] in self.assigned else ''}"
                    for t in _TICKETS]
            return StepResult("\n".join(rows))
        if verb == "read":
            t = self._find(rest)
            if not t:
                return StepResult(f"no ticket {rest!r}")
            return StepResult(f"Subject: {t['subject']}\n\n{t['body']}")
        if verb == "assign":
            parts = rest.split()
            t = self._find(parts[0]) if parts else None
            if not t or len(parts) != 2:
                return StepResult("usage: assign <id> <team>")
            team = parts[1].lower()
            if team not in _TEAMS:
                return StepResult(f"unknown team {parts[1]!r}; teams: {', '.join(_TEAMS)}")
            self.assigned[t["id"]] = team
            return StepResult(f"{t['id']} assigned to {team}.")
        return StepResult(f"unknown command: {action!r}. Commands: {self.actions_help()}")

    def _find(self, tid: str):
        return next((t for t in _TICKETS if t["id"] == tid.strip()), None)

    def _score(self) -> float:
        if self.task.id == "helpdesk.triage":
            correct = sum(1 for t in _TICKETS if self.assigned.get(t["id"]) == t["team"])
            return correct / len(_TICKETS)
        if self.task.id == "helpdesk.billing-sweep":
            billing = {t["id"] for t in _TICKETS if t["team"] == "billing"}
            want = {tid: "billing" for tid in billing}
            return 1.0 if self.assigned == want else 0.0
        return 0.0
