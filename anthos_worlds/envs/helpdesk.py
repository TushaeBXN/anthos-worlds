"""Helpdesk world: route support tickets to the right team."""

from __future__ import annotations

import random
from typing import List

from ..core import Environment, StepResult, Task

_TEAMS = ("billing", "tech", "account")

_CANONICAL_TICKETS = [
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

_POOL = [
    ("billing", "Charged twice this month", "My card shows two subscription charges."),
    ("billing", "Refund for annual plan", "I cancelled in the trial window, please refund."),
    ("billing", "Update card on file", "My credit card expired and I need to change it."),
    ("tech", "App crashes on launch", "The app closes immediately after the update."),
    ("tech", "Cannot upload files", "Uploads fail at 99 percent every time."),
    ("tech", "Site is down", "I get a 500 error on the homepage."),
    ("account", "Change my account email", "I need to update my login email."),
    ("account", "Delete my account", "Please remove my profile and my data."),
    ("account", "Reset two-factor", "I lost my phone and cannot pass 2FA."),
]


class HelpdeskEnv(Environment):
    name = "helpdesk"
    description = ("A support queue. Read tickets and route each to the right "
                   "team: billing, tech, or account.")

    def tasks(self) -> List[Task]:
        return [
            self._triage_task("helpdesk.triage", _CANONICAL_TICKETS),
            self._sweep_task("helpdesk.billing-sweep", _CANONICAL_TICKETS, "billing"),
        ]

    def generate(self, rng: random.Random) -> Task:
        tid = f"helpdesk.gen{rng.randrange(10**6)}"
        sweep_team = rng.choice(_TEAMS) if rng.random() < 0.5 else None
        for _ in range(20):
            picks = rng.sample(_POOL, rng.randint(4, 5))
            if sweep_team is None or any(t == sweep_team for t, _, _ in picks):
                break
        tickets = [{"id": f"t{i + 1}", "subject": subj, "body": body, "team": team}
                   for i, (team, subj, body) in enumerate(picks)]
        if sweep_team:
            return self._sweep_task(tid, tickets, sweep_team)
        return self._triage_task(tid, tickets)

    def solve(self, task: Task) -> List[str]:
        s = task.spec
        if s["kind"] == "triage":
            actions = []
            for t in s["tickets"]:
                actions += [f"read {t['id']}", f"assign {t['id']} {t['team']}"]
            return actions + ["done"]
        actions = []
        for t in s["tickets"]:
            if t["team"] == s["team"]:
                actions += [f"read {t['id']}", f"assign {t['id']} {s['team']}"]
        return actions + ["done"]

    def _triage_task(self, tid: str, tickets: List[dict]) -> Task:
        return Task(tid, "Assign every open ticket to the correct team (billing, "
                         "tech, or account) based on its content. Then say done.",
                    spec={"kind": "triage", "tickets": tickets})

    def _sweep_task(self, tid: str, tickets: List[dict], team: str) -> Task:
        return Task(tid, f"Assign only the {team}-related tickets to the {team} "
                         f"team, touch nothing else, then say done.",
                    spec={"kind": "sweep", "tickets": tickets, "team": team})

    def actions_help(self) -> str:
        return "list | read <id> | assign <id> <team> | done"

    def reset(self, task: Task) -> str:
        self.task = task
        self.tickets = task.spec["tickets"]
        self.assigned = {}
        return (f"Queue: {len(self.tickets)} open tickets. "
                f"Teams: {', '.join(_TEAMS)}. Try: list")

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        if verb == "done":
            return StepResult("queue closed.", self._score(), True)
        if verb == "list":
            rows = [f"[{t['id']}] {t['subject']}"
                    f"{' -> ' + self.assigned[t['id']] if t['id'] in self.assigned else ''}"
                    for t in self.tickets]
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
        return next((t for t in self.tickets if t["id"] == tid.strip()), None)

    def _score(self) -> float:
        s = self.task.spec
        if s["kind"] == "triage":
            correct = sum(1 for t in self.tickets
                          if self.assigned.get(t["id"]) == t["team"])
            return correct / len(self.tickets)
        want = {t["id"]: s["team"] for t in self.tickets if t["team"] == s["team"]}
        return 1.0 if self.assigned == want else 0.0
