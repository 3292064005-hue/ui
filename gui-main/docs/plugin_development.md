# Plugin Development

## IK solver plugin

新 solver 应实现：

- `solve(spec, target, q0, config, *, cancel_flag=None, progress_cb=None, attempt_idx=0)`

并通过 `solver_registry.register('<solver_id>', solver)` 接入。

## Trajectory planner plugin

新 planner 应实现：

- `plan(req)`

并通过 `planner_registry.register('<planner_id>', planner)` 接入。

## Robot importer plugin

新 importer 应实现：

- `load(source, **kwargs)`

并通过 `importer_registry.register('<importer_id>', importer)` 接入。

## Rule

不要把新能力直接写进主窗体或总控制器。先定义 contract，再通过 registry 装配。


## P1 additions

- IK solvers now include `lm` (Levenberg–Marquardt).
- Trajectory validation can consume a lightweight `PlanningScene` with ACM filtering.


## Factory invocation contract

- 通过装配层工厂注册的插件工厂现在在调用前进行签名判定：
  - 若签名可接受上下文字段，则以 `factory(**context)` 调用。
  - 若签名不接受上下文且无必需参数，则以 `factory()` 调用。
- 工厂内部抛出的 `TypeError` 不再被解释为“签名不兼容”；这类错误会按真实执行失败向上抛出。
- 不建议依赖模糊签名或可变位置参数来兼容不同装配环境，推荐显式声明所需上下文字段或使用无参工厂。
