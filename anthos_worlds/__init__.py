"""AnthosWorlds — seven text-simulated agent environments in one framework.

    from anthos_worlds import make, run_bench, RandomAgent

    report = run_bench(RandomAgent())
    print(report.table())
"""

from .agents import (Agent, LLMAgent, RandomAgent, ScriptedAgent,
                     anthropic_backend, openai_compat_backend,
                     transformers_backend)
from .bench import (BenchReport, export_sft, run_bench, run_episode,
                    save_traces)
from .core import Environment, Episode, Step, StepResult, Task
from .envs import ALL_ENVS, env_names, make
from .oracle import ORACLE_SCRIPTS, oracle_agent

__version__ = "0.1.0"

__all__ = [
    "ALL_ENVS", "Agent", "BenchReport", "Environment", "Episode", "LLMAgent",
    "ORACLE_SCRIPTS", "RandomAgent", "ScriptedAgent", "Step", "StepResult",
    "Task", "anthropic_backend", "env_names", "export_sft", "make",
    "openai_compat_backend", "oracle_agent", "run_bench", "run_episode",
    "save_traces", "transformers_backend",
]
