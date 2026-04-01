# Robot Sim Engine

基于纯数学推导的多自由度机械臂运动学与轨迹规划仿真引擎。

## 当前版本重点

- 统一版本真源：`VersionCatalog` / app / export / session / benchmark pack / 文档口径对齐
- 正式任务生命周期：`TaskState`、`TaskSnapshot`、worker structured events、增强版 `ThreadOrchestrator`
- importer V7：`RobotModelBundle`、importer registry 与 importer 实现拆分、fidelity 明文化
- trajectory 校验拆分为 validators：timing / path metrics / goal / limits / collision
- GUI 协调层：新增 coordinators，开始将 MainWindow 的任务编排逻辑下沉

当前交付版本为 **V7 工程硬化版**。在 V3 的可运行基础上，这一版进一步补硬了平台能力：

- 标准 D-H 建模、FK、中间变换缓存、解析几何 Jacobian
- 数值 IK：Pseudo-inverse / DLS / LM / 自适应阻尼 / 加权最小二乘 / position-only / 零空间二级目标
- 解析 IK：新增 `analytic_6r` 球腕 6R 闭式求解插件（当前对 PUMA-like 标准 DH 样机可用）
- IK 稳定性增强：粗工作空间预检查、失败自动多起点重试、结果诊断、solver registry、请求约束适配器流水线
- 请求约束适配器：初值限位修复、目标旋转矩阵正交化、姿态失败时的 position-only 定向降级重试
- 四元数、SO(3) 对数映射、Slerp、五次多项式轨迹规划
- Joint-space、Cartesian-pose、Trapezoidal 插件轨迹与 Waypoint Graph 规划骨架
- `JointTrajectory` 预缓存 FK，并记录 feasibility / quality / collision summary / metadata
- 轻量 collision 预检查：AABB broad-phase、自碰撞风险、环境碰撞风险、clearance metric
- Benchmark：默认 case pack、baseline compare、solver matrix（含解析 6R solver）
- Export：trajectory bundle、metrics、benchmark、session、完整 ZIP package
- Registry / plugin contracts：solver、planner、robot importer
- 导入适配：YAML robot config 与简化 URDF importer
- PySide6 GUI、Qt worker、Benchmark 面板、Diagnostics 面板、Scene Toolbar、Package Export 入口
- pytest 单元 / 集成 / benchmark / performance / GUI smoke（GUI 测试按依赖自动跳过）
- GitHub Actions CI：执行 `ruff check`、`mypy`（针对核心数学/领域/轨迹模型）以及带 coverage gate 的 `pytest --cov`
- pre-commit：提供 ruff / mypy / pytest 本地提交前门禁
- 当前测试基线：**以 CI / pytest 实际收集结果为准**
- 发布打包：使用 `python scripts/package_release.py --output dist/release.zip --top-level-dir robot_sim_engine` 生成洁净交付包（自动排除缓存/覆盖率/本地工件）

## V7 质量门禁

- quick quality：`ruff check src tests`、targeted `mypy`、`python scripts/verify_quality_contracts.py`、`pytest tests/unit tests/regression -q`
- full validation：`pytest --cov=src/robot_sim --cov-report=term-missing -q`，coverage `fail_under = 80`
- gui smoke：在 **Ubuntu 22.04 + Python 3.10 + PySide6>=6.5** 环境执行 `pytest tests/gui -q`
- quality contracts：`docs/quality_gates.md`、`docs/module_status.md`、`docs/capability_matrix.md`、`docs/exception_catch_matrix.md` 必须与运行时服务真源一致
- contract regeneration：执行 `python scripts/regenerate_quality_contracts.py` 后，`docs/` 目录不得产生未提交 diff

## Experimental 模块

以下模块当前明确标记为 experimental，不纳入稳定主链承诺：

- `presentation.widgets.collision_panel`
- `presentation.widgets.export_panel`
- `presentation.widgets.scene_options_panel`
- `render.picking`
- `render.plot_sync`

## 运行环境与版本约束

- 操作系统：**Ubuntu 22.04 LTS**（项目计划书中的首选验证环境）
- Python：**3.10+**，CI 与本地建议优先使用 **3.10** 以保持与计划书、类型配置和 GUI 依赖基线一致
- GUI 框架：**PySide6 >= 6.5**
- 3D 渲染：**PyVista >= 0.43**、**pyvistaqt >= 0.11**
- 2D 曲线：**pyqtgraph >= 0.13**

说明：README、`pyproject.toml`、CI 工作流和计划书应保持这一运行基线一致。

## 配置 Profile

- `configs/profiles/default.yaml`：共享默认基线
- `configs/profiles/dev.yaml`：本地开发配置
- `configs/profiles/ci.yaml`：CI 回归配置
- `configs/profiles/gui.yaml`：GUI 运行配置
- `configs/profiles/release.yaml`：发布打包配置
- `configs/profiles/research.yaml`：研究/实验能力开启配置（允许 experimental backend / plugin discovery）

`ConfigService` 采用 **代码默认值 -> default profile -> 指定 profile -> 本地 app.yaml / solver.yaml** 的合并顺序，避免环境口径再次漂移。


## Runtime Feature Policy

- 默认 / GUI / CI / release profile 均关闭 experimental 模块运行时启用、experimental backend 宣告与外部 plugin discovery
- `research.yaml` 显式开启：
  - `experimental_modules_enabled`
  - `experimental_backends_enabled`
  - `plugin_discovery_enabled`
- 外部插件必须先在 `configs/plugins.yaml` 中白名单声明，才允许被受控装配层接入
- repo 级广义异常捕获边界由 `docs/exception_catch_matrix.md` 与 `python scripts/verify_quality_contracts.py` 共同约束

## 快速开始

```bash
pip install -e .[dev]
python scripts/run_tests.py
python -m pytest -q
```

安装 GUI 依赖后可运行图形界面：

```bash
pip install -e .[gui,dev]
python -m robot_sim.app.main
```

## 目录

```text
src/robot_sim/
  app/            启动、版本、依赖装配
  domain/         能力描述、错误、plugin 契约
  model/          FK / IK / trajectory / benchmark / export manifest 等数据模型
  core/           纯数学核心、trajectory / collision 子系统
  application/    DTO、registry、use case、service、worker
  presentation/   Qt 主窗体、controller、线程编排、widget
  render/         3D / 2D 渲染、截图、plot sync
  infra/          配置、日志、schema、文件
```

## 当前可直接演示的链路

- 加载样例机器人
- 编辑 DH / home q 并保存 YAML
- 执行 FK / IK
- 生成关节空间轨迹、笛卡尔位姿轨迹、Trapezoidal 轨迹
- 轨迹播放、曲线游标同步、3D 机械臂联动
- 运行 benchmark，并导出 JSON / CSV / ZIP package
- 导入简化 URDF 机器人配置
- 导出 trajectory bundle、trajectory metrics、benchmark report、session、完整实验包

## 工程约束

- `core/` 不依赖 Qt
- GUI 中的 IK / trajectory / benchmark / playback 都必须走 worker
- 3D 视图尽量走 actor 持久更新而不是全量 `clear()`
- 新增 solver / planner / importer 必须通过 registry 接入
- 轨迹对象必须能被日志、诊断和导出解释，不能只靠动画展示


## Runtime resource and export resolution

- 启动装配链现在通过 `robot_sim.app.runtime_paths.resolve_runtime_paths()` 统一解析运行时路径，而不是要求所有调用方自行拼接 repo 根目录。
- `bootstrap()` 与 `build_container()` 仍保持原有外部调用方式兼容，但容器内部已显式区分：`project_root`、`resource_root`、`config_root`、`robot_root`、`plugin_manifest_path`、`export_root`。
- GUI 截图、导出服务、package export 统一写入 `export_root`。可通过环境变量 `ROBOT_SIM_EXPORT_DIR` 覆盖默认导出目录。
- wheel / 安装态运行优先使用包内 `robot_sim.resources.configs` 资源；源码态运行继续优先使用仓库 `configs/`。

## Playback cache contract

- `JointTrajectory` 现在会依据真实缓存数组状态规范化 `cache_status`，不再把 metadata 声明无条件视为真。
- live playback 主链要求轨迹满足 `trajectory.is_playback_ready`；GUI 不再在播放帧应用时做 UI 线程 FK fallback。
- 当轨迹已生成但缓存未就绪时，界面会明确提示缓存状态，而不是静默同步重算整条轨迹。
