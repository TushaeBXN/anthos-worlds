"""Oracle: a programmatic solver-agent.

Every environment implements ``solve(task)``, so the oracle can complete any
task — canonical or procedurally generated. Two jobs: (1) prove in CI that
every task the generators emit is solvable, (2) produce unlimited perfect
demonstration episodes: ``--agent oracle --variants 50 --sft out.jsonl``
generates training data without spending a single model token.
"""

from .agents import Agent


class OracleAgent(Agent):
    name = "oracle"

    def act(self, env, task, episode) -> str:
        plan = env.solve(task)
        i = len(episode.steps)
        return plan[i] if i < len(plan) else "done"


def oracle_agent() -> OracleAgent:
    return OracleAgent()
