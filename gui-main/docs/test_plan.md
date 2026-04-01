# Test Plan

## Unit

- D-H / FK 正确性
- Jacobian 解析构造
- Quaternion round-trip
- SO(3) exp/log
- Quintic boundary conditions
- IK diagnostics / retry / unreachable handling
- ConfigService / RobotRegistry schema validation
- ExportService trajectory bundle / benchmark CSV / package export
- PlaybackService / PlaybackController 状态推进
- ValidateTrajectoryUseCase feasibility / quality / collision summary 计算
- Benchmark service / use case / baseline compare
- Registry / importer / retiming / compare solver 用例

## Integration

- Reachable IK
- Position-only IK
- Unreachable IK graceful failure
- Cartesian trajectory sampling + per-sample IK
- MainController benchmark / export 主链路

## GUI smoke

在安装 `PySide6` 与 `pytest-qt` 后启用：

- MainWindow 实例化
- load robot -> run IK -> plan trajectory
- playback pause / stop / seek
- benchmark run -> export report
- package export

## Benchmark / performance

- 默认 case pack 不得无故退化
- benchmark baseline compare 必须输出
- 轻量 performance smoke 至少验证 IK / export / planning 主链路可运行

## Regression criteria

- 所有已有测试必须通过
- benchmark 成功率不得无故下降
- trajectory quality / feasibility / collision summary 不得被新改动破坏
- 导出格式字段保持版本化兼容
