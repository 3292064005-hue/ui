from dataclasses import dataclass
from typing import Any


@dataclass
class Event:
    topic: str
    payload: Any
