"""Email world: an inbox to triage — read, reply, forward, archive."""

from __future__ import annotations

import random
from typing import List

from ..core import Environment, StepResult, Task

_CANONICAL_INBOX = [
    {"id": "e1", "from": "boss@corp.com", "subject": "Deadline for the Q3 deck",
     "body": "Can you confirm the deck will be ready by Friday?", "kind": "work"},
    {"id": "e2", "from": "news@dailybytes.io", "subject": "Your Tuesday newsletter",
     "body": "Top 10 gadgets this week...", "kind": "newsletter"},
    {"id": "e3", "from": "alerts@weeklywrap.com", "subject": "Weekly wrap newsletter",
     "body": "This week in markets...", "kind": "newsletter"},
    {"id": "e4", "from": "sam@corp.com", "subject": "lunch?",
     "body": "Tacos at noon?", "kind": "work"},
]

_WORK_POOL = [
    ("boss@corp.com", "Deadline for the Q3 deck", "Can you confirm the deck is ready by Friday?"),
    ("sam@corp.com", "lunch?", "Tacos at noon?"),
    ("cfo@corp.com", "Budget approval needed", "Please confirm the new vendor budget."),
    ("it@corp.com", "Password expiry", "Your password expires Monday."),
    ("hr@corp.com", "Timesheet reminder", "Submit your hours by end of week."),
]
_NEWS_POOL = [
    ("news@dailybytes.io", "Your Tuesday newsletter", "Top 10 gadgets this week..."),
    ("alerts@weeklywrap.com", "Weekly wrap newsletter", "This week in markets..."),
    ("digest@mlweekly.dev", "ML Weekly digest", "New papers this week..."),
]
_KEYWORDS = ["confirmed", "approved", "received", "understood"]


class EmailEnv(Environment):
    name = "email"
    description = "An email inbox. Read, reply, forward, and archive messages."

    def tasks(self) -> List[Task]:
        return [
            self._reply_task("email.confirm", _CANONICAL_INBOX, "e1", "confirmed"),
            self._archive_task("email.declutter", _CANONICAL_INBOX, "newsletter"),
        ]

    def generate(self, rng: random.Random) -> Task:
        work = rng.sample(_WORK_POOL, rng.randint(2, 3))
        news = rng.sample(_NEWS_POOL, rng.randint(1, 2))
        raw = [(*m, "work") for m in work] + [(*m, "newsletter") for m in news]
        rng.shuffle(raw)
        inbox = [{"id": f"e{i + 1}", "from": frm, "subject": subj,
                  "body": body, "kind": kind}
                 for i, (frm, subj, body, kind) in enumerate(raw)]
        tid = f"email.gen{rng.randrange(10**6)}"
        if rng.random() < 0.5:
            target = rng.choice([m for m in inbox if m["kind"] == "work"])
            return self._reply_task(tid, inbox, target["id"], rng.choice(_KEYWORDS))
        return self._archive_task(tid, inbox, "newsletter")

    def solve(self, task: Task) -> List[str]:
        s = task.spec
        if s["kind"] == "reply":
            return [f"read {s['target']}",
                    f"reply {s['target']} {s['keyword']}, thank you for the note.",
                    "done"]
        targets = [m["id"] for m in s["inbox"] if m["kind"] == s["target_kind"]]
        return [f"archive {mid}" for mid in targets] + ["done"]

    def _reply_task(self, tid: str, inbox: List[dict], target: str, keyword: str) -> Task:
        msg = next(m for m in inbox if m["id"] == target)
        return Task(tid, f"Reply to the email from {msg['from']} with subject "
                         f"'{msg['subject']}'; your reply must contain the word "
                         f"'{keyword}'. Then say done.",
                    spec={"kind": "reply", "inbox": inbox, "target": target,
                          "keyword": keyword})

    def _archive_task(self, tid: str, inbox: List[dict], target_kind: str) -> Task:
        return Task(tid, f"Archive every {target_kind} in the inbox (and nothing "
                         f"else). Then say done.",
                    spec={"kind": "archive", "inbox": inbox,
                          "target_kind": target_kind})

    def actions_help(self) -> str:
        return ("list | read <id> | reply <id> <text> | forward <id> <address> | "
                "archive <id> | done")

    def reset(self, task: Task) -> str:
        self.task = task
        self.inbox = task.spec["inbox"]
        self.archived: List[str] = []
        self.replies: List[dict] = []
        return f"Inbox: {len(self.inbox)} messages. Try: list"

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        if verb == "done":
            return StepResult("inbox closed.", self._score(), True)
        if verb == "list":
            rows = [f"[{m['id']}] from {m['from']}: {m['subject']}"
                    for m in self.inbox if m["id"] not in self.archived]
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
        return next((m for m in self.inbox if m["id"] == mid.strip()), None)

    def _score(self) -> float:
        s = self.task.spec
        if s["kind"] == "reply":
            return 1.0 if any(r["to"] == s["target"]
                              and s["keyword"] in r["text"].lower()
                              for r in self.replies) else 0.0
        targets = {m["id"] for m in self.inbox if m["kind"] == s["target_kind"]}
        return 1.0 if set(self.archived) == targets else 0.0
