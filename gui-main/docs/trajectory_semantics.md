# Trajectory semantics

- `goal_position_error` / `goal_orientation_error` measure final state vs explicit target pose or target joint goal.
- `start_to_end_position_delta` / `start_to_end_orientation_delta` measure intrinsic displacement across the produced trajectory and are not target errors.
- Path generation, retiming, and validation are separate stages.


## Cache integrity and playback readiness

- `JointTrajectory.cache_status` 会根据 `ee_positions`、`joint_positions`、`ee_rotations` 与样本数一致性做归一化。
- `ready` / `recomputed` 只在缓存完整时成立；若数组缺失或长度不一致，会自动降级为 `partial` 或 `none`。
- validation 阶段允许为诊断目的做 FK fallback，但该 fallback 不等价于“轨迹已具备 playback cache”。
- presentation/playback 主链必须以 `trajectory.is_playback_ready` 作为进入 live playback 的硬门槛。
