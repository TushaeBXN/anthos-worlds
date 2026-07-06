"""Terminal world: a virtual filesystem driven by shell-like commands."""

from __future__ import annotations

import random
from typing import Dict, List

from ..core import Environment, StepResult, Task

_WORDS = ["quarterly", "budget", "roadmap", "onboarding", "handover", "launch"]
_DIRS = ["reports", "archive", "projects", "drafts", "backup"]
_NEW_FILES = ["summary.txt", "plan.txt", "todo.txt", "minutes.txt"]
_ROOT_FILES = ["notes.txt", "tmp.log", "draft.txt", "old.csv", "scratch.md"]

_DEFAULT_FILES = {"/notes.txt": "meeting notes", "/tmp.log": "debug debug"}


class TerminalEnv(Environment):
    name = "terminal"
    description = "A virtual unix-like filesystem. Manipulate files and directories."

    def tasks(self) -> List[Task]:
        return [
            self._create_task("terminal.report", "/reports", "summary.txt", "quarterly"),
            self._cleanup_task("terminal.cleanup", "/notes.txt", "/archive", "/tmp.log"),
        ]

    def generate(self, rng: random.Random) -> Task:
        tid = f"terminal.gen{rng.randrange(10**6)}"
        if rng.random() < 0.5:
            return self._create_task(tid, "/" + rng.choice(_DIRS),
                                     rng.choice(_NEW_FILES), rng.choice(_WORDS))
        src, delete = rng.sample(_ROOT_FILES, 2)
        return self._cleanup_task(tid, "/" + src, "/" + rng.choice(_DIRS),
                                  "/" + delete)

    def solve(self, task: Task) -> List[str]:
        s = task.spec
        if s["kind"] == "create":
            path = s["dir"].rstrip("/") + "/" + s["file"]
            return [f"mkdir {s['dir']}", f"write {path} {s['word']} update", "done"]
        return [f"mkdir {s['dst_dir']}", f"mv {s['src']} {s['dst_dir']}",
                f"rm {s['delete']}", "done"]

    def _create_task(self, tid: str, d: str, f: str, word: str) -> Task:
        spec = {"kind": "create", "dir": d, "file": f, "word": word,
                "start_files": dict(_DEFAULT_FILES)}
        return Task(tid, f"Create a directory {d} and inside it a file {f} "
                         f"whose content includes the word '{word}'. Then say done.",
                    spec=spec)

    def _cleanup_task(self, tid: str, src: str, dst_dir: str, delete: str) -> Task:
        start = dict(_DEFAULT_FILES)
        start[src] = "important contents"
        start[delete] = "stale data"
        base = src.rsplit("/", 1)[1]
        spec = {"kind": "cleanup", "src": src, "dst_dir": dst_dir,
                "delete": delete, "start_files": start}
        return Task(tid, f"Move {src} into {dst_dir} (as {dst_dir}/{base}) and "
                         f"delete {delete}. Then say done.", spec=spec)

    def actions_help(self) -> str:
        return ("ls <dir> | cat <file> | write <file> <text> | mkdir <dir> | "
                "rm <path> | mv <src> <dst> | done")

    def reset(self, task: Task) -> str:
        self.task = task
        self.files: Dict[str, str] = dict(task.spec["start_files"])
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
        s = self.task.spec
        if s["kind"] == "create":
            content = self.files.get(s["dir"].rstrip("/") + "/" + s["file"], "")
            return 1.0 if s["word"].lower() in content.lower() else 0.0
        moved_to = s["dst_dir"].rstrip("/") + "/" + s["src"].rsplit("/", 1)[1]
        moved = moved_to in self.files and s["src"] not in self.files
        deleted = s["delete"] not in self.files
        return (0.5 * moved) + (0.5 * deleted)
