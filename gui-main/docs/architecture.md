# Architecture

## Layers

- `model`: FK / IK / trajectory / benchmark / export manifest 等不可变结果对象。
- `core`: 纯数学内核，不依赖 Qt。
- `application`: DTO、registry、use case、service、worker，是业务编排中间层。
- `presentation`: 主窗体、线程编排器、分层 controller、widget。
- `render`: PyVista / pyqtgraph 适配层、截图、plot sync。
- `infra`: 配置、日志、文件、schema。

## Registry / Plugin entry

V4 开始，以下能力通过 registry 接入：

- `solver_registry`: IK solver
- `planner_registry`: trajectory planner
- `importer_registry`: robot importer

后续新增 6R 解析 IK、冗余约束求解、URDF importer、collision adapter 时，不应再直接修改主控制器或主窗口。

## Presentation split

当前 GUI 编排拆成：

- `RobotController`: 机器人加载、保存、FK、采样
- `IKController`: 目标位姿构造、IK request 构造、结果回写
- `TrajectoryController`: joint/cartesian 轨迹 request 构造与应用
- `PlaybackController`: 播放索引、帧切换、倍率和循环控制
- `BenchmarkController`: benchmark config 构造与批量运行
- `ExportController`: trajectory / benchmark / metrics / session / package 导出
- `DiagnosticsController`: 当前会话诊断快照

## Threading rules

1. `core` 不能导入 Qt。
2. IK / trajectory / benchmark / playback / export 都优先走 worker。
3. GUI 线程只做参数收集、状态更新和渲染调用。
4. 取消与停止必须通过统一线程编排器传播。

## Data rules

1. 轨迹对象必须携带 `metadata / feasibility / quality`。
2. Playback 优先使用预缓存 FK 结果，而不是每帧在 UI 线程重算。
3. Euler angles 只允许出现在 UI 输入层，IK 核心使用旋转矩阵 / rotation vector / quaternion。
4. 导出对象必须版本化并能被离线分析脚本复用。


## Runtime path model

- `bootstrap()` / `build_container()` 使用 `RuntimePaths` 作为统一运行时路径真源。
- `project_root` 只表示源码工程根或兼容根语义；资源读取、插件清单读取、机器人配置读取、导出目录写入必须走显式路径字段。
- GUI / controller / facade 不允许再直接硬编码 `project_root / "exports"` 或 `project_root / "configs"`。

## Coordinator dependency rule

- coordinator 主路径通过显式注入获取 facade、thread orchestrator 与 view contract。
- 兼容 fallback 仅作为迁移期旁路保留，不再作为主路径依赖解析手段。
- `project_playback_stopped()` 与 `project_trajectory_result()` 已移除通过 action 回流触发 seek 的主路径。
