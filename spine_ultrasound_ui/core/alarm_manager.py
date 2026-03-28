from dataclasses import dataclass
from typing import List, Optional


@dataclass
class AlarmRecord:
    severity: str
    source: str
    message: str
    auto_action_taken: str = ""


class AlarmManager:
    def __init__(self):
        self.records: List[AlarmRecord] = []

    def push(self, severity: str, source: str, message: str, auto_action_taken: str = ""):
        self.records.append(AlarmRecord(severity, source, message, auto_action_taken))

    def latest(self) -> Optional[AlarmRecord]:
        return self.records[-1] if self.records else None
