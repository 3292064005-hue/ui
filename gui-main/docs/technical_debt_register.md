# Technical Debt Register

## 已关闭

- 版本口径分散：已统一到 `VersionCatalog`
- `MainWindow` 单文件过重：已拆成 `main_window.py` + mixins
- importer registry 与 importer 实现混放：已拆分
- trajectory validator 大一统：已拆分为 validators
- 任务生命周期字符串散落：已统一为 `TaskState` / `TaskSnapshot` / structured worker events
- `ThreadOrchestrator` 缺失 `queue_latest` / timeout 异常流：已补齐
- `PlanTrajectoryUseCase` 残留 `v4` 版本漂移：已改为 `v7` 版本真源

## 当前已知边界

- GUI / render 层仍允许轻量兼容壳模块存在；这些模块在 `module_status.md` 中标记为 experimental
- CI 默认以 Ubuntu 22.04 + Python 3.10 作为一致性基线，GUI 相关测试仍会按依赖自动跳过
- `mypy` 仍聚焦关键核心路径，未宣称对全部 GUI 壳层进行完全类型化治理

## 后续建议

- 若进入 V8，优先继续下沉 MainWindow mixin 业务到 coordinator / facade
- 为 GUI 交互链补更深的 offscreen 回归与截图基线
- 继续收紧广义异常捕获颗粒度，减少 GUI 兼容层中的 `except Exception`


## 本轮已收口债务

- 运行时路径寻址：已统一到 `RuntimePaths`，源码态/安装态共享同一装配语义。
- GUI 导出路径硬编码：已收口到 `RuntimeFacade.export_root`。
- trajectory/playback 缓存边界：已禁止 live playback 在 UI 线程做 FK fallback。
- plugin factory `TypeError` 误吞：已改为签名判定后调用。
- `ThreadOrchestrator` 单文件多职责：已拆分内部职责模块，外部 API 保持不变。

## 仍保留的兼容旁路

- coordinator 构造仍允许在测试或旧调用链下从 window/controller 获取依赖，但这条路径已不是主路径。
- `bootstrap()` 继续返回 `(project_root, container)` 以保持既有调用方兼容；实际资源装配则通过 `container.runtime_paths` 获取。
