"""Email world: an inbox to triage — read, reply, forward, archive."""

from __future__ import annotations

from typing import List

from ..core import Environment, StepResult, Task

_INBOX = [
    {"id": "e1", "from": "boss@corp.com", "subject": "Deadline for the Q3 deck",
     "body": "Can you confirm the deck will be ready by Friday?", "kind": "work"},
    {"id": "e2", "from": "news@dailybytes.io", "subject": "Your Tuesday newsletter",
     "body": "Top 10 gadgets this week...", "kind": "newsletter"},
    {"id": "e3", "from": "alerts@weeklywrap.com", "subject": "Weekly wrap newsletter",
     "body": "This week in markets...", "kind": "newsletter"},
    {"id": "e4", "from": "sam@corp.com", "subject": "lunch?",
     "body": "Tacos at noon?", "kind": "work"},
]


class EmailEnv(Environment):
    name = "email"
    description = "An email inbox. Read, reply, forward, and archive messages."

    def tasks(self) -> List[Task]:
        return [
            Task("email.confirm",
                 "Reply to the email from your boss about the deadline; your "
                 "reply must contain the word 'confirmed'. Then say done."),
            Task("email.declutter",
                 "Archive every newsletter in the inbox (and nothing else). "
                 "Then say done."),
        ]

    def actions_help(self) -> str:
        return ("list | read <id> | reply <id> <text> | forward <id> <address> | "
                "archive <id> | done")

    def reset(self, task: Task) -> str:
        self.task = task
        self.archived: List[str] = []
        self.replies: List[dict] = []
        return f"Inbox: {len(_INBOX)} messages. Try: list"

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        if verb == "done":
            return StepResult("inbox closed.", self._score(), True)
        if verb == "list":
            rows = [f"[{m['id']}] from {m['from']}: {m['subject']}"
                    for m in _INBOX if m["id"] not in self.archived]
            return StepResult("\n".join(rows) or "(inbox empty)")
        if verb == "read":
            m = self._find(rest)
            if not m:
                return StepResult(f"no message {rest!r}")
            return StepResult(f"From: {m['from']}\nSubject: {m['subject']}\n\n{m['body']}")
        if verb == "reply":
            parts = rest.split(None, 1)
            m = self._find(parts[0] if parts else "")
            if not m or len(parts) < 2:
                return StepResult("usage: reply <id> <text>")
            self.replies.append({"to": m["id"], "text": parts[1]})
            return StepResult("reply sent.")
        if verb == "forward":
            parts = rest.split(None, 1)
            if len(parts) < 2 or not self._find(parts[0]):
                return StepResult("usage: forward <id> <address>")
            return StepResult("forwarded.")
        if verb == "archive":
            m = self._find(rest)
            if not m:
                return StepResult(f"no message {rest!r}")
            if m["id"] not in self.archived:
                self.archived.append(m["id"])
            return StepResult("archived.")
        return StepResult(f"unknown command: {action!r}. Commands: {self.actions_help()}")

    def _find(self, mid: str):
        return next((m for m in _INBOX if m["id"] == mid.strip()), None)

    def _score(self) -> float:
        if self.task.id == "email.confirm":
            return 1.0 if any(r["to"] == "e1" and "confirmed" in r["text"].lower()
                              for r in self.replies) else 0.0
        if self.task.id == "email.declutter":
            newsletters = {m["id"] for m in _INBOX if m["kind"] == "newsletter"}
            return 1.0 if set(self.archived) == newsletters else 0.0
        return 0.0
