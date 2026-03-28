# IPC Protocol

本工程采用本机双通道 IPC：

- Command Channel: TCP REQ/REP, default `127.0.0.1:5656`
- Telemetry Channel: TCP PUB/SUB-style fanout, default `127.0.0.1:5657`
- All envelopes include `protocol_version = 1`

## 1. Command Envelope

```json
{
  "protocol_version": 1,
  "command": "start_scan",
  "payload": {"scan_speed": 8.0},
  "request_id": "uuid"
}
```

## 2. Reply Envelope

```json
{
  "protocol_version": 1,
  "ok": true,
  "message": "start_scan accepted",
  "request_id": "uuid",
  "data": {}
}
```

## 3. Telemetry Envelope

```json
{
  "protocol_version": 1,
  "topic": "robot_state",
  "ts_ns": 1234567890,
  "data": {}
}
```

## 4. Commands

- `connect_robot`
- `disconnect_robot`
- `power_on`
- `power_off`
- `set_auto_mode`
- `set_manual_mode`
- `validate_setup`
- `lock_session`
- `load_scan_plan`
- `approach_prescan`
- `seek_contact`
- `start_scan`
- `pause_scan`
- `resume_scan`
- `safe_retreat`
- `go_home`
- `clear_fault`
- `emergency_stop`

`lock_session` payload 约定至少包含：
- `experiment_id`
- `session_id`
- `session_dir`
- `config_snapshot`
- `device_roster`
- `software_version`
- `build_id`
- `scan_plan_hash`

`load_scan_plan` payload 约定包含完整 `scan_plan` 对象。

## 5. Topics

### core_state
- execution_state
- armed
- fault_code
- active_segment
- progress_pct
- session_id

### robot_state
- powered
- operate_mode
- joint_pos
- joint_vel
- joint_torque
- cart_force
- tcp_pose
- last_event
- last_controller_log

### contact_state
- mode
- confidence
- pressure_current
- recommended_action

### scan_progress
- active_segment
- path_index
- overall_progress
- frame_id

### device_health
- devices

### safety_status
- safe_to_arm
- safe_to_scan
- active_interlocks

### recording_status
- session_id
- recording
- dropped_samples
- last_flush_ns

### quality_feedback
- image_quality
- feature_confidence
- quality_score
- need_resample

### alarm_event
- severity
- source
- message
- session_id
- segment_id
- event_ts_ns
