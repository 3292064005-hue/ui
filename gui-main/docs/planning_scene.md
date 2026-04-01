# Planning Scene / ACM

P1 引入了轻量级 `PlanningScene` 抽象，用于统一环境障碍物、允许碰撞矩阵（ACM）与 scene revision。

当前实现范围：

- 环境障碍物以 `AABB` 近似体表达
- `AllowedCollisionMatrix` 可忽略 link-link 或 link-object 配对
- `ValidateTrajectoryUseCase` 可接受 `planning_scene`，并输出：
  - `scene_revision`
  - `collision_level`
  - `ignored_pairs`
  - `self_pairs`
  - `environment_pairs`

当前仍不包含：

- 连续碰撞检测
- FCL / mesh 级精确碰撞
- 多 collision backend 切换
