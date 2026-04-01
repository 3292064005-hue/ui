# Benchmark Suite

每台样例机器人默认包含以下 case 类型：

- `home_pose`
- `mid_pose`
- `orientation_shifted`
- `position_only_hard`
- `near_limit_pose`
- `near_singular_pose`
- `unreachable_far`

## 输出指标

- `success_rate`
- `p50_elapsed_ms`
- `p95_elapsed_ms`
- `mean_final_pos_err`
- `mean_final_ori_err`
- `mean_restarts_used`
- `stop_reason_histogram`
- `comparison`（与 baseline 的差异）

## 用途

- 验证 solver 改动是否退化
- 对比不同 IK 参数组合
- 形成答辩或展示用的量化报告
- 作为回归治理工具，而不是只做展示
