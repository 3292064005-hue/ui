Patch Notes - Optimized V1
==========================

1. Added playback subsystem
   - PlaybackState extended with speed multiplier and loop policy
   - PlaybackService / StepPlaybackUseCase / PlaybackWorker added
   - PlaybackPanel now supports play, pause, step, stop, seek, speed, loop

2. Controller and state flow hardened
   - Centralized state access through StateStore
   - Trajectory planning and playback now update SessionState consistently
   - Session export and trajectory export integrated into controller

3. Render and plots improved
   - Scene3DWidget now supports playback marker updates
   - SceneController caches end-effector path and updates trajectory visuals
   - PlotsManager supports persistent cursors for playback sync

4. Robot configuration and registry improved
   - RobotSpec now supports display_name, description, metadata
   - RobotRegistry preserves stored id vs display name and metadata roundtrip
   - RobotConfigPanel can save edited DH rows and home_q

5. Validation and metrics improved
   - InputValidator clamps joint goals and validates home_q vs limits
   - MetricsService summarizes trajectory statistics in addition to IK metrics

6. Test suite expanded
   - Added playback, validator, metadata roundtrip, and trajectory metrics tests

Patch Notes - Optimized V2
==========================

7. IK solver upgraded
   - Added adaptive damping and weighted least-squares handling
   - IK logs now track damping, score, and clipping status
   - Failure stop reasons expanded: workspace_precheck, position_unreachable, orientation_not_satisfied,
     singularity_stall, joint_limit_blocked, step_clipping_saturation

8. Trajectory subsystem expanded
   - Added Cartesian pose trajectory mode with linear position interpolation + quaternion Slerp
   - Cartesian planner now runs sequential IK with soft-accept fallback for near-singular samples
   - JointTrajectory now caches ee_rotations in addition to ee_positions and joint_positions

9. Configuration and validation hardened
   - ConfigService now validates app/solver schemas before use
   - solver.yaml expanded with adaptive_damping / weighted_least_squares defaults
   - RobotRegistry now validates finite values, limit ordering, and home_q consistency

10. Export and diagnostics improved
   - Trajectory export now writes compressed NPZ bundles with cached FK data and metadata
   - Session export now includes IK diagnostics and trajectory metadata
   - MetricsService now reports final damping and trajectory jerk proxy

11. Benchmark foundation added
   - Added BenchmarkService with default case generation and report output structure
   - Provides repeatable reachable / hard / unreachable IK evaluation cases

12. Test suite expanded again
   - Added config validation, IK diagnostics, export bundle, benchmark, and Cartesian trajectory tests
   - Total regression suite now covers 31 tests
