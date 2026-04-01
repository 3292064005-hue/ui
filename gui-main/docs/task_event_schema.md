# Task Event Schema

Worker 统一发射 progress / finished / failed 事件，并由 `ThreadOrchestrator` 投影为 `TaskSnapshot`。
