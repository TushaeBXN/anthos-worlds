"""Agents: anything that maps (instruction, history, observation) -> action.

``LLMAgent`` works with any chat backend — Anthropic's API, an
OpenAI-compatible server (vLLM/Ollama on a cloud GPU box), or a local
HuggingFace model — so the same bench scores your fine-tunes and the
frontier models side by side.
"""

from __future__ import annotations

import os
import random
import re
from abc import ABC, abstractmethod
from typing import Callable, Dict, List

from .core import Environment, Episode, Task

Messages = List[Dict[str, str]]


class Agent(ABC):
    name: str = "agent"

    @abstractmethod
    def act(self, env: Environment, task: Task, episode: Episode) -> str:
        """Return the next plain-text action given the episode so far."""


class RandomAgent(Agent):
    """Baseline: issues random documented commands. Every bench needs a floor."""

    name = "random"

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)

    def act(self, env, task, episode) -> str:
        verbs = [part.strip().split()[0]
                 for part in env.actions_help().split("|") if part.strip()]
        return self.rng.choice(verbs)


class ScriptedAgent(Agent):
    """Replays a fixed action sequence per task id. Used in tests and as an
    oracle to sanity-check that every task is solvable."""

    name = "scripted"

    def __init__(self, scripts: Dict[str, List[str]]) -> None:
        self.scripts = scripts
        self._cursor: Dict[str, int] = {}

    def act(self, env, task, episode) -> str:
        i = self._cursor.get(task.id, 0)
        script = self.scripts.get(task.id, [])
        self._cursor[task.id] = i + 1
        return script[i] if i < len(script) else "done"


_SYSTEM = """You are an agent acting inside a simulated environment.

Environment: {env_description}
Available commands (one per turn):
{actions_help}

Your goal: {instruction}

Reply with EXACTLY ONE command per turn — the bare command only, no
explanation, no quotes, no markdown."""


class LLMAgent(Agent):
    """Drives any chat LLM. ``complete(messages) -> str`` does the model call."""

    name = "llm"

    def __init__(self, complete: Callable[[Messages], str], name: str = "llm") -> None:
        self.complete = complete
        self.name = name

    def act(self, env, task, episode) -> str:
        messages: Messages = [{
            "role": "system",
            "content": _SYSTEM.format(env_description=env.description,
                                      actions_help=env.actions_help(),
                                      instruction=task.instruction),
        }, {"role": "user", "content": episode.first_observation}]
        for step in episode.steps:
            messages.append({"role": "assistant", "content": step.action})
            messages.append({"role": "user", "content": step.observation})
        return _clean(self.complete(messages))


def _clean(reply: str) -> str:
    """Take the first plausible command line out of a model reply."""
    reply = re.sub(r"```[a-z]*", "", reply).strip().strip("`\"'")
    for line in reply.splitlines():
        line = line.strip().strip("`\"'")
        if line:
            return line
    return reply


# ---------------------------------------------------------------- backends

def anthropic_backend(model: str = "claude-sonnet-5",
                      max_tokens: int = 200) -> Callable[[Messages], str]:
    import anthropic  # lazy: optional dependency
    client = anthropic.Anthropic()

    def complete(messages: Messages) -> str:
        system = messages[0]["content"]
        resp = client.messages.create(model=model, max_tokens=max_tokens,
                                      system=system, messages=messages[1:])
        return resp.content[0].text

    return complete


def openai_compat_backend(model: str, base_url: str = None,
                          max_tokens: int = 200) -> Callable[[Messages], str]:
    """Works with vLLM, Ollama, llama.cpp server, or OpenAI itself."""
    from openai import OpenAI  # lazy: optional dependency
    client = OpenAI(base_url=base_url or os.environ.get("OPENAI_BASE_URL"))

    def complete(messages: Messages) -> str:
        resp = client.chat.completions.create(model=model, messages=messages,
                                              max_tokens=max_tokens)
        return resp.choices[0].message.content or ""

    return complete


def transformers_backend(model_name: str, max_new_tokens: int = 64,
                         **load_kwargs) -> Callable[[Messages], str]:
    """Local HuggingFace chat model (e.g. your Anthos Qwen LoRA merge)."""
    import torch  # lazy: optional dependency
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
    model.eval()

    def complete(messages: Messages) -> str:
        prompt = tokenizer.apply_chat_template(messages, tokenize=False,
                                               add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_new_tokens,
                                 do_sample=False,
                                 pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:],
                                skip_special_tokens=True)

    return complete
