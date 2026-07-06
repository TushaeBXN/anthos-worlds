"""AnthosWorlds Bench: run an agent across all seven worlds and score it.

Every episode is recorded; successful episodes export to chat-format SFT
JSONL so bench runs double as training-data generation for fine-tuning.
"""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .agents import Agent
from .core import Episode, Step
from .envs import env_names, make

_SFT_SYSTEM = """You are an agent acting inside a simulated environment.

Environment: {env_description}
Available commands (one per turn):
{actions_help}

Your goal: {instruction}

Reply with EXACTLY ONE command per turn."""


def run_episode(env, task, agent: Agent) -> Episode:
    first = env.reset(task)
    episode = Episode(env=env.name, task=task, first_observation=first)
    for _ in range(task.max_steps):
        action = agent.act(env, task, episode)
        result = env.step(action)
        episode.steps.append(Step(action=action, observation=result.observation))
        episode.reward = result.reward
        if result.done:
            break
    return episode


@dataclass
class BenchReport:
    agent: str
    episodes: List[Episode] = field(default_factory=list)

    def by_env(self) -> Dict[str, Dict[str, float]]:
        stats: Dict[str, Dict[str, float]] = {}
        for name in sorted({e.env for e in self.episodes}):
            eps = [e for e in self.episodes if e.env == name]
            stats[name] = {
                "tasks": len(eps),
                "success_rate": sum(e.success for e in eps) / len(eps),
                "mean_reward": sum(e.reward for e in eps) / len(eps),
                "mean_steps": sum(len(e.steps) for e in eps) / len(eps),
            }
        return stats

    @property
    def overall_reward(self) -> float:
        if not self.episodes:
            return 0.0
        return sum(e.reward for e in self.episodes) / len(self.episodes)

    def table(self) -> str:
        rows = [f"AnthosWorlds Bench — agent: {self.agent}", "",
                f"{'world':<12}{'tasks':>6}{'success':>10}{'reward':>9}{'steps':>8}"]
        for name, s in self.by_env().items():
            rows.append(f"{name:<12}{s['tasks']:>6}{s['success_rate']:>10.0%}"
                        f"{s['mean_reward']:>9.2f}{s['mean_steps']:>8.1f}")
        rows.append("")
        rows.append(f"overall mean reward: {self.overall_reward:.3f}")
        return "\n".join(rows)


def run_bench(agent: Agent, envs: Optional[Sequence[str]] = None,
              traces_path: Optional[str] = None, variants: int = 0,
              seed: int = 0) -> BenchReport:
    """Run the bench. ``variants`` adds that many procedurally generated tasks
    per world, seeded per-world so results are reproducible regardless of
    which subset of worlds you run."""
    report = BenchReport(agent=agent.name)
    for name in envs or env_names():
        env = make(name)
        tasks = list(env.tasks())
        if variants:
            rng = random.Random(f"{seed}:{name}")
            tasks += [env.generate(rng) for _ in range(variants)]
        for task in tasks:
            report.episodes.append(run_episode(env, task, agent))
    if traces_path:
        save_traces(report.episodes, traces_path)
    return report


# ------------------------------------------------------------------- traces

def save_traces(episodes: Sequence[Episode], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for e in episodes:
            f.write(json.dumps({
                "env": e.env, "task": e.task.id, "instruction": e.task.instruction,
                "reward": e.reward, "success": e.success,
                "first_observation": e.first_observation,
                "steps": [{"action": s.action, "observation": s.observation}
                          for s in e.steps],
            }) + "\n")


def export_sft(episodes: Sequence[Episode], path: str,
               successful_only: bool = True) -> int:
    """Convert episodes to chat-format JSONL ready for SFT fine-tuning."""
    exported = 0
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for e in episodes:
            if successful_only and not e.success:
                continue
            env = make(e.env)
            messages = [{"role": "system", "content": _SFT_SYSTEM.format(
                env_description=env.description, actions_help=env.actions_help(),
                instruction=e.task.instruction)}]
            observation = e.first_observation
            for step in e.steps:
                messages.append({"role": "user", "content": observation})
                messages.append({"role": "assistant", "content": step.action})
                observation = step.observation
            f.write(json.dumps({"messages": messages}) + "\n")
            exported += 1
    return exported
