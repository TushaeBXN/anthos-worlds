# AnthosWorlds

**Seven text-simulated agent environments in one framework — plus a bench that scores any LLM on all of them, and a trace exporter that turns bench runs into fine-tuning data.**

By [Anthos Intelligence](https://github.com/TushaeBXN/anthos). Everything is text in, text out: an environment hands the agent an observation, the agent replies with one plain-text command. No tool schemas, no browser drivers, no Docker — any chat model can play, from a frontier API to your own fine-tune served on a cloud GPU.

## The seven worlds

| world | the agent must... |
|---|---|
| `terminal` | manipulate a virtual filesystem with shell-like commands |
| `shop` | search a catalog and check out under price/rating constraints |
| `email` | triage an inbox — reply, forward, archive the right messages |
| `calendar` | book meetings around existing conflicts |
| `quest` | explore a text adventure, collect items, reach the goal |
| `warehouse` | drive a grid robot moving crates to target cells |
| `helpdesk` | read support tickets and route each to the correct team |

Every world ships deterministic tasks with programmatic rewards in [0, 1] — no LLM judge, no flaky scoring.

## Quickstart

```bash
pip install -e .

# sanity floor: a random agent
python -m anthos_worlds.cli --agent random

# ceiling: the built-in oracle solves all 14 tasks
python -m anthos_worlds.cli --agent oracle

# score a frontier model (needs ANTHROPIC_API_KEY, pip install anthropic)
python -m anthos_worlds.cli --agent anthropic --model claude-sonnet-5

# score your own model served by vLLM/Ollama on a cloud GPU box
python -m anthos_worlds.cli --agent openai --model anthos-qwen \
    --base-url http://your-gpu-box:8000/v1
```

Output is a per-world table:

```
AnthosWorlds Bench — agent: oracle

world        tasks   success   reward   steps
calendar         2      100%     1.00     3.0
email            2      100%     1.00     3.5
...
overall mean reward: 1.000
```

## As a library

```python
import anthos_worlds as aw

env = aw.make("quest")
task = env.tasks()[0]
obs = env.reset(task)            # gym-style: reset -> observation
result = env.step("go down")     # step -> StepResult(observation, reward, done)

# drive any chat function
agent = aw.LLMAgent(aw.anthropic_backend("claude-sonnet-5"))
report = aw.run_bench(agent, traces_path="runs/claude.jsonl")
print(report.table())
```

Writing your own world is ~80 lines: subclass `Environment`, implement `tasks()`, `actions_help()`, `reset()`, `step()`, and register it in `anthos_worlds/envs/__init__.py`.

## From bench to training data

Episodes convert directly into chat-format SFT data — the same loop that evaluates your model generates its next training set:

```bash
# 14 perfect demonstrations, zero model tokens spent
python -m anthos_worlds.cli --agent oracle --sft data/oracle_sft.jsonl
```

```python
n = aw.export_sft(report.episodes, "data/sft.jsonl", successful_only=True)
```

Each line is `{"messages": [{role, content}, ...]}` — feed it straight to a TRL/axolotl SFT run on your cloud GPU, then serve the result with vLLM and point the bench back at it to measure the improvement. That's the flywheel: **bench → traces → fine-tune → bench**.

## Roadmap

- [ ] Procedurally generated task variants (seeded) so models can't memorize the 14 shipped tasks
- [ ] Multi-episode held-out split and a public leaderboard
- [ ] Cross-world tasks (read an email, then act in the terminal)
- [ ] RL-style dense rewards as an opt-in

## License

Apache-2.0. © Anthos Intelligence (Brian Tushae Thomas).
