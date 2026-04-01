# Task and threading model

- GUI tasks use worker objects moved to QThread.
- Controllers submit requests; the window projects state only.
- `ThreadOrchestrator` owns task lifecycle state, not business computation.


## Dependency injection rule
Workers and controllers must receive explicit use-case or service dependencies from the container chain. They must not instantiate hidden fallback services inside worker, controller, or window code.


## Internal orchestrator split

`ThreadOrchestrator` 的外部 API 保持不变，但内部职责已拆分为：

- `presentation.threading.task_handle`
- `presentation.threading.submission_policy`
- `presentation.threading.lifecycle_registry`
- `presentation.threading.timeout_supervisor`
- `presentation.threading.qt_runtime_bridge`
- `presentation.threading.worker_binding`

这次拆分的目标是降低单文件变更密度；并未改变既有调度策略、worker 生命周期语义或外部调用方式。
