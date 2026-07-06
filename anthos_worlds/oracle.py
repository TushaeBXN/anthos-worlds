"""Oracle: hand-written solutions for every shipped task.

Two jobs: (1) prove in CI that every task is solvable, (2) generate perfect
demonstration episodes — ``--agent oracle --sft out.jsonl`` gives you
fine-tuning data without spending a single model token.
"""

from .agents import ScriptedAgent

ORACLE_SCRIPTS = {
    "terminal.report": ["mkdir /reports",
                        "write /reports/summary.txt quarterly results are strong",
                        "done"],
    "terminal.cleanup": ["mkdir /archive", "mv /notes.txt /archive",
                         "rm /tmp.log", "done"],
    "shop.laptop": ["search laptop", "view p1", "add p1", "checkout"],
    "shop.gifts": ["search gift", "add p4", "add p5", "cart", "checkout"],
    "email.confirm": ["read e1",
                      "reply e1 Confirmed — the deck will be ready by Friday.",
                      "done"],
    "email.declutter": ["list", "archive e2", "archive e3", "done"],
    "calendar.sync": ["list tuesday", "book tuesday 12 1 sync", "done"],
    "calendar.review": ["list thursday", "book thursday 13 2 review",
                        "cancel standup", "done"],
    "quest.chest": ["go down", "look", "take key", "go up", "go up", "use key"],
    "quest.rope": ["go down", "take rope", "go up", "done"],
    "warehouse.single": ["west", "west", "grab", "east", "east", "east",
                         "north", "north", "drop"],
    "warehouse.swap-lane": ["west", "north", "grab", "south", "south", "south",
                            "drop", "east", "east", "east", "grab",
                            "north", "north", "north", "north", "drop"],
    "helpdesk.triage": ["list", "read t1", "assign t1 billing",
                        "read t2", "assign t2 tech",
                        "read t3", "assign t3 account",
                        "read t4", "assign t4 billing", "done"],
    "helpdesk.billing-sweep": ["read t1", "assign t1 billing",
                               "read t4", "assign t4 billing", "done"],
}


def oracle_agent() -> ScriptedAgent:
    agent = ScriptedAgent(ORACLE_SCRIPTS)
    agent.name = "oracle"
    return agent
