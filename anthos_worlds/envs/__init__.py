"""The seven worlds. ``make(name)`` returns a fresh environment instance."""

from typing import Dict, List, Type

from ..core import Environment
from .calendar import CalendarEnv
from .email import EmailEnv
from .helpdesk import HelpdeskEnv
from .quest import QuestEnv
from .shop import ShopEnv
from .terminal import TerminalEnv
from .warehouse import WarehouseEnv

ALL_ENVS: Dict[str, Type[Environment]] = {
    cls.name: cls
    for cls in (TerminalEnv, ShopEnv, EmailEnv, CalendarEnv,
                QuestEnv, WarehouseEnv, HelpdeskEnv)
}


def make(name: str) -> Environment:
    if name not in ALL_ENVS:
        raise KeyError(f"unknown environment '{name}'; have: {sorted(ALL_ENVS)}")
    return ALL_ENVS[name]()


def env_names() -> List[str]:
    return list(ALL_ENVS)
