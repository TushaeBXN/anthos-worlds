"""Command line: ``python -m anthos_worlds.cli --agent random``"""

from __future__ import annotations

import argparse

from .agents import LLMAgent, RandomAgent, anthropic_backend, openai_compat_backend
from .bench import export_sft, run_bench
from .envs import env_names


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AnthosWorlds bench.")
    parser.add_argument("--agent", default="random",
                        choices=["random", "oracle", "anthropic", "openai"],
                        help="which agent plays the worlds")
    parser.add_argument("--model", default=None,
                        help="model id for llm agents "
                             "(e.g. claude-sonnet-5 or a vLLM-served name)")
    parser.add_argument("--base-url", default=None,
                        help="OpenAI-compatible server URL (vLLM/Ollama)")
    parser.add_argument("--envs", nargs="*", default=None,
                        help=f"subset of worlds; default all: {env_names()}")
    parser.add_argument("--variants", type=int, default=0,
                        help="procedurally generated task variants per world")
    parser.add_argument("--seed", type=int, default=0,
                        help="seed for generated variants (reproducible)")
    parser.add_argument("--traces", default=None,
                        help="write raw episode traces to this JSONL path")
    parser.add_argument("--sft", default=None,
                        help="export successful episodes as SFT JSONL")
    args = parser.parse_args()

    if args.agent == "random":
        agent = RandomAgent()
    elif args.agent == "oracle":
        from .oracle import oracle_agent
        agent = oracle_agent()
    elif args.agent == "anthropic":
        agent = LLMAgent(anthropic_backend(args.model or "claude-sonnet-5"),
                         name=args.model or "claude-sonnet-5")
    else:
        if not args.model:
            parser.error("--agent openai requires --model")
        agent = LLMAgent(openai_compat_backend(args.model, args.base_url),
                         name=args.model)

    report = run_bench(agent, envs=args.envs, traces_path=args.traces,
                       variants=args.variants, seed=args.seed)
    print(report.table())
    if args.sft:
        n = export_sft(report.episodes, args.sft)
        print(f"\nexported {n} successful episodes to {args.sft}")


if __name__ == "__main__":
    main()
