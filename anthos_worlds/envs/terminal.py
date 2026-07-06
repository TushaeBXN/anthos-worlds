"""Terminal world: a virtual filesystem driven by shell-like commands."""

from __future__ import annotations

from typing import Dict, List

from ..core import Environment, StepResult, Task


class TerminalEnv(Environment):
    name = "terminal"
    description = "A virtual unix-like filesystem. Manipulate files and directories."

    def tasks(self) -> List[Task]:
        return [
            Task("terminal.report",
                 "Create a directory /reports and inside it a file summary.txt "
                 "whose content includes the word 'quarterly'. Then say done."),
            Task("terminal.cleanup",
                 "Move /notes.txt into /archive (as /archive/notes.txt) and "
                 "delete /tmp.log. Then say done."),
        ]

    def actions_help(self) -> str:
        return ("ls <dir> | cat <file> | write <file> <text> | mkdir <dir> | "
                "rm <path> | mv <src> <dst> | done")

    def reset(self, task: Task) -> str:
        self.task = task
        self.files: Dict[str, str] = {"/notes.txt": "meeting notes",
                                      "/tmp.log": "debug debug"}
        self.dirs = {"/", "/home"}
        return f"$ you are at /. Directories: {sorted(self.dirs)}. Files: {sorted(self.files)}"

    def step(self, action: str) -> StepResult:
        verb, rest = self.parse(action)
        if verb == "done":
            return StepResult("session closed.", self._score(), True)
        if verb == "ls":
            path = self._norm(rest or "/")
            names = [f for f in self.files if f.startswith(path.rstrip("/") + "/")
                     or (path == "/" and f.count("/") == 1)]
            subdirs = [d for d in self.dirs if d != path and d.startswith(path.rstrip('/') + '/')]
            return StepResult(f"{sorted(subdirs)} {sorted(names)}")
        if verb == "cat":
            path = self._norm(rest)
            if path in self.files:
                return StepResult(self.files[path])
            return StepResult(f"cat: {path}: no such file")
        if verb == "mkdir":
            self.dirs.add(self._norm(rest))
            return StepResult("ok")
        if verb == "write":
            parts = rest.split(None, 1)
            if len(parts) < 2:
                return StepResult("usage: write <file> <text>")
            path = self._norm(parts[0])
            parent = path.rsplit("/", 1)[0] or "/"
            if parent not in self.dirs:
                return StepResult(f"write: directory {parent} does not exist (mkdir it first)")
            self.files[path] = parts[1]
            return StepResult("ok")
        if verb == "rm":
            path = self._norm(rest)
            if self.files.pop(path, None) is not None:
                return StepResult("ok")
            return StepResult(f"rm: {path}: no such file")
        if verb == "mv":
            parts = rest.split()
            if len(parts) != 2:
                return StepResult("usage: mv <src> <dst>")
            src, dst = self._norm(parts[0]), self._norm(parts[1])
            if src not in self.files:
                return StepResult(f"mv: {src}: no such file")
            if dst in self.dirs or dst.endswith("/"):
                dst = dst.rstrip("/") + "/" + src.rsplit("/", 1)[1]
            parent = dst.rsplit("/", 1)[0] or "/"
            if parent not in self.dirs:
                return StepResult(f"mv: directory {parent} does not exist (mkdir it first)")
            self.files[dst] = self.files.pop(src)
            return StepResult("ok")
        return StepResult(f"unknown command: {action!r}. Commands: {self.actions_help()}")

    def _norm(self, path: str) -> str:
        path = path.strip()
        return path if path.startswith("/") else "/" + path

    def _score(self) -> float:
        if self.task.id == "terminal.report":
            content = self.files.get("/reports/summary.txt", "")
            return 1.0 if "quarterly" in content.lower() else 0.0
        if self.task.id == "terminal.cleanup":
            moved = "/archive/notes.txt" in self.files and "/notes.txt" not in self.files
            deleted = "/tmp.log" not in self.files
            return (0.5 * moved) + (0.5 * deleted)
        return 0.0
