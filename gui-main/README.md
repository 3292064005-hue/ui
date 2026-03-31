# Spine Ultrasound Platform

正式主线固定为 Ubuntu 22.04。

这个仓库现在只保留两条正式产品路径：

- 桌面主线：`run.py --backend mock|core|api`
- Headless/Web 适配层：`spine_ultrasound_ui.api_server:app`

不再保留历史开发壳、第二套协议栈、第二套 runtime，或未接入构建与测试的“名义主线”。

## v9 Mainline hardening

- 新增 **唯一控制权主线**：写命令现在可以通过控制租约（lease）显式绑定到 actor / workspace / session，避免多控制源并发写入。
- 新增 **会话证据封印**：session 冻结后会生成 `session_evidence_seal.json`，对 manifest 与 artifact registry 做正式摘要与哈希封印。
- headless API 新增：`/api/v1/control-authority`、`/api/v1/control-lease/acquire`、`/api/v1/control-lease/release`、`/api/v1/sessions/current/evidence-seal`。
- API CORS 不再默认全开放，改为由 `SPINE_ALLOWED_ORIGINS` 驱动，并默认限制为本地开发源。

## Mainline Layout

- `cpp_robot_core/`
  唯一机器人控制核心，正式 runtime 名称统一为 `spine_robot_core`
- `spine_ultrasound_ui/`
  PySide6 桌面主线、session/workflow 编排、图像与回放能力
- `ui_frontend/`
  可选 Web 消费端，只能通过 headless v1 adapter 访问主线状态
- `configs/force_control.json`
  力控阈值、默认接触力和安全回缩距离的唯一正式来源
- `BridgeObservabilityService`
  前端必须对关键遥测、关键执行态和关键命令结果形成观测证据，才能进入正式启动门禁

## Supported Environment

- OS: `Ubuntu 22.04`
- Python: `3.11+`
- C++ toolchain: `cmake`, `g++`, `protobuf`, `OpenSSL`, `Eigen3`
- Node.js: `20.x` for `ui_frontend/`

`requirements.txt` 是 Ubuntu 22.04 主线最小依赖。
`requirements-clinical.txt` 是在主线之上的 Ubuntu 22.04 临床扩展依赖。

## Setup

### Python mainline

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Optional clinical extension

```bash
python -m pip install -r requirements-clinical.txt
```

### Optional web frontend

```bash
cd ui_frontend
npm ci
```

## Run

### Desktop in mock mode

```bash
python run.py --backend mock
```

### Desktop against the mock core server

```bash
python scripts/mock_robot_core_server.py
# new terminal
SPINE_UI_BACKEND=core python run.py --backend core
```


### Desktop via headless API bridge

```bash
uvicorn spine_ultrasound_ui.api_server:app --host 0.0.0.0 --port 8000
# new terminal
python run.py --backend api --api-base-url http://127.0.0.1:8000
```

### Build and start `spine_robot_core`

如果已经挂载 SDK：

```bash
export XCORE_SDK_ROOT=/opt/rokae/librokae
```

然后：

```bash
cmake -S cpp_robot_core -B cpp_robot_core/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp_robot_core/build -j
./cpp_robot_core/build/spine_robot_core
```

### Start the headless adapter

```bash
./scripts/start_headless.sh
```

or:

```bash
uvicorn spine_ultrasound_ui.api_server:app --host 0.0.0.0 --port 8000
```

## Environment doctor

在进入真实 `robot_core + xCore SDK` 主线前，先执行：

```bash
python scripts/doctor_runtime.py
```

它会检查：Python/CMake/C++/Protobuf/OpenSSL、TLS runtime 目录、`XCORE_SDK_ROOT` / `ROKAE_SDK_ROOT`、以及 remote/local IP 与主线链路设置。

## Verification

仓库级唯一正式验收命令：

```bash
./scripts/verify_mainline.sh
```

它会按 Ubuntu 22.04 主线顺序执行：

- repo hygiene 检查
- `python -m pytest -q`
- `cmake` / `ctest`
- `cd ui_frontend && npm ci && npm run build`

如果本机安装了 ROS 或第三方 pytest 插件，优先使用 `python -m pytest`，避免外部插件污染主线测试面。

## Product Rules

- 桌面端会将当前运行配置持久化到 `workspace/runtime/runtime_config.json`
- 桌面端会将窗口布局和最近页面保存到 `workspace/runtime/ui_preferences.json`
- UI 中所有关键按钮必须提供明确的可执行条件或阻塞原因
- 正式协议只有一套：TLS 1.3 + length-prefixed Protobuf
- 正式消息只有三类：`Command`、`Reply`、`TelemetryEnvelope`
- `protocol_version` 不匹配必须在进入业务逻辑前拒绝
- `cpp_robot_core` 是唯一执行状态源
- Python 保留 workflow / session 语义，但不复制执行状态机
- `AppController` 的关键命令链必须具备明确失败动作、回退日志和用户提示

## Documents

- 架构总则：[ARCHITECTURE.md](ARCHITECTURE.md)
- 主线收敛框架：[docs/STRONG_CONVERGENCE_FRAMEWORK.md](docs/STRONG_CONVERGENCE_FRAMEWORK.md)
- IPC 合同：[docs/IPC_PROTOCOL.md](docs/IPC_PROTOCOL.md)
- Headless API v1 合同：[docs/HEADLESS_API_V1.md](docs/HEADLESS_API_V1.md)

## Current Mainline Outcomes

- `run.py --backend mock|core|api` 是唯一正式桌面入口
- `spine_ultrasound_ui.api_server:app` 是唯一正式 headless/Web 入口
- `configs/force_control.json` 统一驱动 Python schema、mock runtime、C++ 力控默认值与测试阈值
- `ui_frontend` 只消费 `/api/v1/*` 和 `/ws/*`，不再直连另一套协议栈

## SDK runtime governance surfaces

当前桌面主线已经补齐 4 个与 xCore SDK 对齐的正式治理面：

- `系统准备`：显示 robot class / RT mode / IP / link / SDK blocker / readiness
- `视觉与路径`：显示路径摘要、执行 profile 选择、近似 xMateModel 前检与 DH/包络信息
- `机器人监控`：显示 controller log、RL 工程、路径库、I/O 快照、拖动示教和 motion contract
- `实验回放`：显示路径/拖动/RL 资产摘要，便于研究复盘

这些页面统一由：

- `SdkCapabilityService`：主线对齐与 blocker/warning 生成
- `SdkRuntimeAssetService`：控制器日志、RL、路径库、I/O、安全配置聚合
- `XMateModelService`：路径前检、包络、连续性、DH 摘要

驱动，而不是在页面里散落硬编码判断。


## Mainline governance additions

当前桌面主线又补齐了 3 个正式治理面：

- `ClinicalConfigService`：对运行参数做基线校验与 xMate 主线默认值回填，不再只看 SDK/模型 blocker
- `SessionGovernanceService`：把 release gate、integrity、resume、incident、selected execution 聚合成会话治理摘要
- `governance_snapshot.json`：支持把当前 readiness / config / SDK / model / session governance 一次性导出为治理快照

桌面现在可以直接执行：

- 应用 `xMate` 主线基线
- 导出治理快照
- 刷新会话治理

## Clinical mainline guardrails

- 机器人控制主权保留在 C++ / xCore SDK 主线
- UI 不进入 1 kHz RT 回调
- `directTorque` 不进入临床主线
- 正式启动前必须通过 SDK blocker + safety contract + model precheck
- collision / soft limit / singularity governance 现在都进入了正式配置面与运行摘要


## Frontend-backend link mainline

这一轮主线把“桌面 UI 直连 backend”扩成了三种正式互联方式：

- `mock`：桌面内嵌 mock runtime
- `core`：桌面直接连 `robot_core` TLS/Protobuf
- `api`：桌面通过 `FastAPI + WebSocket` 桥接 headless adapter

新增能力：

- `ApiBridgeBackend`：UI 可通过 `/api/v1/*` 与 `/ws/*` 接入 backend
- `/api/v1/runtime-config`：前端运行配置可正式同步到 headless adapter
- `BackendLinkService`：统一聚合 REST 可达性、telemetry/camera/ultrasound 流状态、命令成功率与链路 blocker/warning
- UI readiness 现在把“前后端链路在线”纳入正式检查项
- `BackendControlPlaneService`：统一检查协议一致性、运行配置漂移、topic 覆盖和最近命令窗口
- `/api/v1/control-plane` 与 `/api/v1/commands/recent`：headless 正式暴露控制面状态，不再只给 link alive
- UI readiness 进一步把“前后端配置一致 / 控制面协议一致”纳入正式检查项


## Recent architecture waves

- Wave A control-plane rewrite: desktop command provenance now routes through `CommandOrchestrator`; desktop governance/status projection is centralized in `GovernanceCoordinator`, `SessionFacade`, and `UiProjectionService`; headless control-plane output now exposes deployment profile and unified control-plane snapshot.



## TLS material

- The repository no longer commits a reusable private key.
- Generate local development TLS material with `./scripts/generate_dev_tls_cert.sh`.
- For shared or clinical deployments, provide `ROBOT_CORE_TLS_CERT` and `ROBOT_CORE_TLS_KEY` from a secure secret store.


- docs/CONTROL_PLANE_REWRITE_WAVE_C.md
