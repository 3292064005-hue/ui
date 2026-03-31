#include "robot_core/core_runtime.h"

#include <algorithm>
#include <cmath>
#include <filesystem>

#include "json_utils.h"
#include "robot_core/force_state.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

namespace {

constexpr int kProtocolVersion = 1;

std::string stateName(RobotCoreState state) {
  switch (state) {
    case RobotCoreState::Boot: return "BOOT";
    case RobotCoreState::Disconnected: return "DISCONNECTED";
    case RobotCoreState::Connected: return "CONNECTED";
    case RobotCoreState::Powered: return "POWERED";
    case RobotCoreState::AutoReady: return "AUTO_READY";
    case RobotCoreState::SessionLocked: return "SESSION_LOCKED";
    case RobotCoreState::PathValidated: return "PATH_VALIDATED";
    case RobotCoreState::Approaching: return "APPROACHING";
    case RobotCoreState::ContactSeeking: return "CONTACT_SEEKING";
    case RobotCoreState::ContactStable: return "CONTACT_STABLE";
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::RecoveryRetract: return "RECOVERY_RETRACT";
    case RobotCoreState::SegmentAborted: return "SEGMENT_ABORTED";
    case RobotCoreState::PlanAborted: return "PLAN_ABORTED";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

DeviceHealth makeDevice(const std::string& name, bool online, const std::string& detail) {
  DeviceHealth device;
  device.device_name = name;
  device.online = online;
  device.fresh = online;
  device.detail = detail;
  return device;
}

std::vector<double> filledVector(size_t count, double value) {
  return std::vector<double>(count, value);
}

std::string objectArray(const std::vector<std::string>& entries) {
  std::string out = "[";
  for (size_t idx = 0; idx < entries.size(); ++idx) {
    if (idx > 0) {
      out += ",";
    }
    out += entries[idx];
  }
  out += "]";
  return out;
}

std::string summaryEntry(const std::string& name, const std::string& detail) {
  return json::object({
      json::field("name", json::quote(name)),
      json::field("detail", json::quote(detail)),
  });
}

std::string logEntryJson(const std::string& level, const std::string& source, const std::string& message) {
  return json::object({
      json::field("level", json::quote(level)),
      json::field("source", json::quote(source)),
      json::field("message", json::quote(message)),
  });
}

std::string boolMapJson(const std::map<std::string, bool>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) {
    fields.push_back(json::field(key, json::boolLiteral(value)));
  }
  return json::object(fields);
}

std::string doubleMapJson(const std::map<std::string, double>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) {
    fields.push_back(json::field(key, json::formatDouble(value)));
  }
  return json::object(fields);
}

std::string intMapJson(const std::map<std::string, int>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) {
    fields.push_back(json::field(key, std::to_string(value)));
  }
  return json::object(fields);
}

std::string projectArrayJson(const std::vector<SdkRobotProjectInfo>& projects) {
  std::vector<std::string> entries;
  for (const auto& project : projects) {
    entries.push_back(json::object({
        json::field("name", json::quote(project.name)),
        json::field("tasks", json::stringArray(project.tasks)),
    }));
  }
  return objectArray(entries);
}

std::string pathArrayJson(const std::vector<SdkRobotPathInfo>& paths) {
  std::vector<std::string> entries;
  for (const auto& path : paths) {
    entries.push_back(json::object({
        json::field("name", json::quote(path.name)),
        json::field("rate", json::formatDouble(path.rate)),
        json::field("points", std::to_string(path.points)),
    }));
  }
  return objectArray(entries);
}

std::string vectorJson(const std::vector<double>& values) { return json::array(values); }

std::string dhArrayJson(const std::vector<OfficialDhParameter>& params) {
  std::vector<std::string> entries;
  for (const auto& item : params) {
    entries.push_back(json::object({
        json::field("joint", std::to_string(item.joint)),
        json::field("a_mm", json::formatDouble(item.a_mm)),
        json::field("alpha_rad", json::formatDouble(item.alpha_rad, 4)),
        json::field("d_mm", json::formatDouble(item.d_mm)),
        json::field("theta_rad", json::formatDouble(item.theta_rad, 4)),
    }));
  }
  return objectArray(entries);
}

std::vector<double> array6ToVector(const std::array<double, 6>& values) {
  return std::vector<double>(values.begin(), values.end());
}

std::vector<double> array16ToVector(const std::array<double, 16>& values) {
  return std::vector<double>(values.begin(), values.end());
}

std::vector<double> array3ToVector(const std::array<double, 3>& values) {
  return std::vector<double>(values.begin(), values.end());
}

}  // namespace

CoreRuntime::CoreRuntime() {
  nrt_motion_service_.bind(&sdk_robot_);
  rt_motion_service_.bindSdkFacade(&sdk_robot_);
  devices_ = {
      makeDevice("robot", false, "机械臂控制器未连接"),
      makeDevice("camera", false, "摄像头未连接"),
      makeDevice("pressure", false, "压力传感器未连接"),
      makeDevice("ultrasound", false, "超声设备未连接"),
  };
  recovery_manager_.setRetrySettleWindow(std::chrono::milliseconds(static_cast<int>(force_limits_.force_settle_window_ms)));
}

void CoreRuntime::setState(RobotCoreState state) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (execution_state_ != state) {
    last_transition_ = stateName(state);
  }
  execution_state_ = state;
}

RobotCoreState CoreRuntime::state() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return execution_state_;
}

std::string CoreRuntime::handleCommandJson(const std::string& line) {
  std::lock_guard<std::mutex> lock(mutex_);
  const auto request_id = json::extractString(line, "request_id");
  const auto command = json::extractString(line, "command");
  if (command == "connect_robot") {
    if (execution_state_ != RobotCoreState::Boot && execution_state_ != RobotCoreState::Disconnected) {
      return replyJson(request_id, false, "robot already connected");
    }
    const auto remote_ip = json::extractString(line, "remote_ip", sdk_robot_.runtimeConfig().remote_ip);
    const auto local_ip = json::extractString(line, "local_ip", sdk_robot_.runtimeConfig().local_ip);
    if (!sdk_robot_.connect(remote_ip, local_ip)) {
      return replyJson(request_id, false, "connect_robot failed");
    }
    controller_online_ = true;
    execution_state_ = RobotCoreState::Connected;
    devices_[0] = makeDevice("robot", true, std::string("robot_core 已连接 / source=") + sdk_robot_.runtimeSource());
    devices_[1] = makeDevice("camera", true, "摄像头在线");
    devices_[2] = makeDevice("pressure", true, "压力传感器在线");
    devices_[3] = makeDevice("ultrasound", true, "超声设备在线");
    return replyJson(request_id, true, "connect_robot accepted");
  }
  if (command == "disconnect_robot") {
    recording_service_.closeSession();
    sdk_robot_.disconnect();
    execution_state_ = RobotCoreState::Disconnected;
    controller_online_ = false;
    powered_ = false;
    automatic_mode_ = false;
    tool_ready_ = false;
    tcp_ready_ = false;
    load_ready_ = false;
    pressure_fresh_ = false;
    robot_state_fresh_ = false;
    rt_jitter_ok_ = true;
    fault_code_.clear();
    session_id_.clear();
    session_dir_.clear();
    plan_id_.clear();
    plan_hash_.clear();
    locked_scan_plan_hash_.clear();
    plan_loaded_ = false;
    total_points_ = 0;
    total_segments_ = 0;
    path_index_ = 0;
    frame_id_ = 0;
    active_segment_ = 0;
    active_waypoint_index_ = 0;
    retreat_ticks_remaining_ = 0;
    progress_pct_ = 0.0;
    pressure_current_ = 0.0;
    contact_stable_since_ns_ = 0;
    last_transition_.clear();
    state_reason_.clear();
    contact_state_ = ContactTelemetry{};
    pending_alarms_.clear();
    recovery_manager_.resetToIdle();
    last_final_verdict_ = FinalVerdict{};
    injected_faults_.clear();
    devices_ = {
        makeDevice("robot", false, "机械臂控制器未连接"),
        makeDevice("camera", false, "摄像头未连接"),
        makeDevice("pressure", false, "压力传感器未连接"),
        makeDevice("ultrasound", false, "超声设备未连接"),
    };
    return replyJson(request_id, true, "disconnect_robot accepted");
  }
  if (command == "power_on") {
    if (!controller_online_) {
      return replyJson(request_id, false, "robot not connected");
    }
    if (!sdk_robot_.setPower(true)) {
      return replyJson(request_id, false, "power_on failed");
    }
    powered_ = true;
    execution_state_ = RobotCoreState::Powered;
    return replyJson(request_id, true, "power_on accepted");
  }
  if (command == "power_off") {
    if (controller_online_) {
      sdk_robot_.setPower(false);
    }
    powered_ = false;
    automatic_mode_ = false;
    execution_state_ = controller_online_ ? RobotCoreState::Connected : RobotCoreState::Disconnected;
    return replyJson(request_id, true, "power_off accepted");
  }
  if (command == "set_auto_mode") {
    if (!powered_) {
      return replyJson(request_id, false, "robot not powered");
    }
    if (!sdk_robot_.setAutoMode()) {
      return replyJson(request_id, false, "set_auto_mode failed");
    }
    automatic_mode_ = true;
    execution_state_ = RobotCoreState::AutoReady;
    return replyJson(request_id, true, "set_auto_mode accepted");
  }
  if (command == "set_manual_mode") {
    if (controller_online_) {
      sdk_robot_.setManualMode();
    }
    automatic_mode_ = false;
    execution_state_ = powered_ ? RobotCoreState::Powered : RobotCoreState::Connected;
    return replyJson(request_id, true, "set_manual_mode accepted");
  }
  if (command == "validate_setup") {
    const auto safety = evaluateSafetyLocked();
    const auto data_json = json::object({
        json::field("safe_to_arm", json::boolLiteral(safety.safe_to_arm)),
        json::field("safe_to_scan", json::boolLiteral(safety.safe_to_scan)),
        json::field("active_interlocks", json::stringArray(safety.active_interlocks)),
    });
    return replyJson(request_id, safety.safe_to_arm, safety.safe_to_arm ? "setup validated" : "setup invalid", data_json);
  }
  if (command == "compile_scan_plan") {
    const auto verdict = compileScanPlanVerdictLocked(line);
    last_final_verdict_ = verdict;
    const auto verdict_json = finalVerdictJson(verdict);
    return replyJson(request_id, verdict.accepted, verdict.accepted ? "compile_scan_plan accepted" : "compile_scan_plan rejected", json::object({json::field("final_verdict", verdict_json)}));
  }
  if (command == "query_final_verdict") {
    const auto verdict_json = finalVerdictJson(last_final_verdict_);
    return replyJson(request_id, true, "final verdict snapshot", json::object({json::field("final_verdict", verdict_json)}));
  }
  if (command == "query_controller_log") {
    std::vector<std::string> entries;
    for (const auto& item : sdk_robot_.controllerLogs()) {
      entries.push_back(logEntryJson("INFO", "sdk", item));
    }
    return replyJson(request_id, true, "query_controller_log accepted", json::object({json::field("logs", objectArray(entries))}));
  }
  if (command == "query_rl_projects") {
    const auto projects = projectArrayJson(sdk_robot_.rlProjects());
    const auto rl_status = sdk_robot_.rlStatus();
    const auto status = json::object({
        json::field("loaded_project", json::quote(rl_status.loaded_project)),
        json::field("loaded_task", json::quote(rl_status.loaded_task)),
        json::field("running", json::boolLiteral(rl_status.running)),
        json::field("rate", json::formatDouble(rl_status.rate)),
        json::field("loop", json::boolLiteral(rl_status.loop)),
    });
    return replyJson(request_id, true, "query_rl_projects accepted", json::object({json::field("projects", projects), json::field("status", status)}));
  }
  if (command == "query_path_lists") {
    const auto paths = pathArrayJson(sdk_robot_.pathLibrary());
    const auto drag_state = sdk_robot_.dragState();
    const auto drag = json::object({
        json::field("enabled", json::boolLiteral(drag_state.enabled)),
        json::field("space", json::quote(drag_state.space)),
        json::field("type", json::quote(drag_state.type)),
    });
    return replyJson(request_id, true, "query_path_lists accepted", json::object({json::field("paths", paths), json::field("drag", drag)}));
  }
  if (command == "get_io_snapshot") {
    const auto data = json::object({
        json::field("di", boolMapJson(sdk_robot_.di())),
        json::field("do", boolMapJson(sdk_robot_.doState())),
        json::field("ai", doubleMapJson(sdk_robot_.ai())),
        json::field("ao", doubleMapJson(sdk_robot_.ao())),
        json::field("registers", intMapJson(sdk_robot_.registers())),
        json::field("xpanel_vout_mode", json::quote(config_.xpanel_vout_mode)),
    });
    return replyJson(request_id, true, "get_io_snapshot accepted", data);
  }
  if (command == "get_register_snapshot") {
    const auto data = json::object({
        json::field("registers", intMapJson(sdk_robot_.registers())),
        json::field("session_id", json::quote(session_id_)),
        json::field("plan_hash", json::quote(plan_hash_))
    });
    return replyJson(request_id, true, "get_register_snapshot accepted", data);
  }
  if (command == "get_safety_config") {
    const auto data = json::object({
        json::field("collision_detection_enabled", json::boolLiteral(config_.collision_detection_enabled)),
        json::field("collision_sensitivity", std::to_string(config_.collision_sensitivity)),
        json::field("collision_behavior", json::quote(config_.collision_behavior)),
        json::field("collision_fallback_mm", json::formatDouble(config_.collision_fallback_mm)),
        json::field("soft_limit_enabled", json::boolLiteral(config_.soft_limit_enabled)),
        json::field("joint_soft_limit_margin_deg", json::formatDouble(config_.joint_soft_limit_margin_deg)),
        json::field("singularity_avoidance_enabled", json::boolLiteral(config_.singularity_avoidance_enabled))
    });
    return replyJson(request_id, true, "get_safety_config accepted", data);
  }
  if (command == "get_motion_contract") {
    const auto runtime_cfg = sdk_robot_.runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object({
        json::field("rt_mode", json::quote(config_.rt_mode)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("network_tolerance_percent", std::to_string(runtime_cfg.rt_network_tolerance_percent)),
        json::field("preferred_link", json::quote(runtime_cfg.preferred_link)),
        json::field("collision_behavior", json::quote(config_.collision_behavior)),
        json::field("collision_detection_enabled", json::boolLiteral(config_.collision_detection_enabled)),
        json::field("soft_limit_enabled", json::boolLiteral(config_.soft_limit_enabled)),
        json::field("single_control_source_required", json::boolLiteral(runtime_cfg.requires_single_control_source)),
        json::field("clinical_allowed_modes", json::stringArray(identity.clinical_allowed_modes)),
        json::field("cartesian_impedance", vectorJson(config_.cartesian_impedance)),
        json::field("desired_wrench_n", vectorJson(config_.desired_wrench_n)),
        json::field("sdk_boundary_units", json::object({
            json::field("ui_length_unit", json::quote(runtime_cfg.ui_length_unit)),
            json::field("sdk_length_unit", json::quote(runtime_cfg.sdk_length_unit)),
            json::field("boundary_normalized", json::boolLiteral(runtime_cfg.boundary_normalized)),
            json::field("fc_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix_m))),
            json::field("tcp_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix_m))),
            json::field("load_com_m", vectorJson(array3ToVector(runtime_cfg.load_com_m)))
        })),
        json::field("nrt_contract", json::object({
            json::field("active_profile", json::quote(nrt_motion_service_.snapshot().active_profile)),
            json::field("last_command", json::quote(nrt_motion_service_.snapshot().last_command)),
            json::field("command_count", std::to_string(nrt_motion_service_.snapshot().command_count)),
            json::field("degraded_without_sdk", json::boolLiteral(nrt_motion_service_.snapshot().degraded_without_sdk))
        })),
        json::field("rt_contract", json::object({
            json::field("phase", json::quote(rt_motion_service_.snapshot().phase)),
            json::field("last_event", json::quote(rt_motion_service_.snapshot().last_event)),
            json::field("loop_active", json::boolLiteral(rt_motion_service_.snapshot().loop_active)),
            json::field("move_active", json::boolLiteral(rt_motion_service_.snapshot().move_active)),
            json::field("pause_hold", json::boolLiteral(rt_motion_service_.snapshot().pause_hold)),
            json::field("degraded_without_sdk", json::boolLiteral(rt_motion_service_.snapshot().degraded_without_sdk)),
            json::field("desired_contact_force_n", json::formatDouble(rt_motion_service_.snapshot().desired_contact_force_n)),
            json::field("current_period_ms", json::formatDouble(rt_motion_service_.snapshot().current_period_ms))
        })),
        json::field("filters", json::object({
            json::field("joint_hz", json::formatDouble(runtime_cfg.joint_filter_hz)),
            json::field("cart_hz", json::formatDouble(runtime_cfg.cart_filter_hz)),
            json::field("torque_hz", json::formatDouble(runtime_cfg.torque_filter_hz))
        }))
    });
    return replyJson(request_id, true, "get_motion_contract accepted", data);
  }
  if (command == "get_runtime_alignment") {
    const auto runtime_cfg = sdk_robot_.runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object({
        json::field("sdk_family", json::quote("ROKAE xCore SDK (C++)")),
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
        json::field("axis_count", std::to_string(identity.axis_count)),
        json::field("controller_series", json::quote(identity.controller_series)),
        json::field("controller_version", json::quote(identity.controller_version)),
        json::field("remote_ip", json::quote(runtime_cfg.remote_ip)),
        json::field("local_ip", json::quote(runtime_cfg.local_ip)),
        json::field("preferred_link", json::quote(runtime_cfg.preferred_link)),
        json::field("rt_mode", json::quote(config_.rt_mode)),
        json::field("single_control_source", json::boolLiteral(runtime_cfg.requires_single_control_source)),
        json::field("sdk_available", json::boolLiteral(sdk_robot_.sdkAvailable())),
        json::field("source", json::quote(sdk_robot_.runtimeSource()))
    });
    return replyJson(request_id, true, "get_runtime_alignment accepted", data);
  }
  if (command == "get_xmate_model_summary") {
    const auto runtime_cfg = sdk_robot_.runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object({
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("label", json::quote(identity.label)),
        json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
        json::field("axis_count", std::to_string(identity.axis_count)),
        json::field("supported_rt_modes", json::stringArray(identity.supported_rt_modes)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("supports_planner", json::boolLiteral(identity.supports_planner)),
        json::field("supports_xmate_model", json::boolLiteral(identity.supports_xmate_model)),
        json::field("approximate", json::boolLiteral(!(sdk_robot_.xmateModelAvailable() && identity.supports_xmate_model))),
        json::field("source", json::quote(sdk_robot_.runtimeSource())),
        json::field("dh_parameters", dhArrayJson(identity.official_dh_parameters))
    });
    return replyJson(request_id, true, "get_xmate_model_summary accepted", data);
  }
  if (command == "get_sdk_runtime_config") {
    const auto runtime_cfg = sdk_robot_.runtimeConfig();
    const auto data = json::object({
        json::field("robot_model", json::quote(runtime_cfg.robot_model)),
        json::field("sdk_robot_class", json::quote(runtime_cfg.sdk_robot_class)),
        json::field("remote_ip", json::quote(runtime_cfg.remote_ip)),
        json::field("local_ip", json::quote(runtime_cfg.local_ip)),
        json::field("axis_count", std::to_string(runtime_cfg.axis_count)),
        json::field("rt_network_tolerance_percent", std::to_string(runtime_cfg.rt_network_tolerance_percent)),
        json::field("joint_filter_hz", json::formatDouble(runtime_cfg.joint_filter_hz)),
        json::field("cart_filter_hz", json::formatDouble(runtime_cfg.cart_filter_hz)),
        json::field("torque_filter_hz", json::formatDouble(runtime_cfg.torque_filter_hz)),
        json::field("fc_frame_type", json::quote(config_.fc_frame_type)),
        json::field("cartesian_impedance", vectorJson(array6ToVector(runtime_cfg.cartesian_impedance))),
        json::field("desired_wrench_n", vectorJson(array6ToVector(runtime_cfg.desired_wrench_n))),
        json::field("fc_frame_matrix", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix))),
        json::field("tcp_frame_matrix", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix))),
        json::field("load_com_mm", vectorJson(array3ToVector(runtime_cfg.load_com_mm))),
        json::field("fc_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix_m))),
        json::field("tcp_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix_m))),
        json::field("load_com_m", vectorJson(array3ToVector(runtime_cfg.load_com_m))),
        json::field("ui_length_unit", json::quote(runtime_cfg.ui_length_unit)),
        json::field("sdk_length_unit", json::quote(runtime_cfg.sdk_length_unit)),
        json::field("boundary_normalized", json::boolLiteral(runtime_cfg.boundary_normalized)),
        json::field("load_inertia", vectorJson(array6ToVector(runtime_cfg.load_inertia)))
    });
    return replyJson(request_id, true, "get_sdk_runtime_config accepted", data);
  }
  if (command == "get_identity_contract") {
    const auto runtime_cfg = sdk_robot_.runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object({
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("label", json::quote(identity.label)),
        json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
        json::field("axis_count", std::to_string(identity.axis_count)),
        json::field("controller_series", json::quote(identity.controller_series)),
        json::field("controller_version", json::quote(identity.controller_version)),
        json::field("preferred_link", json::quote(identity.preferred_link)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("supported_rt_modes", json::stringArray(identity.supported_rt_modes)),
        json::field("clinical_allowed_modes", json::stringArray(identity.clinical_allowed_modes)),
        json::field("cartesian_impedance_limits", vectorJson(identity.cartesian_impedance_limits)),
        json::field("desired_wrench_limits", vectorJson(identity.desired_wrench_limits)),
        json::field("official_dh_parameters", dhArrayJson(identity.official_dh_parameters))
    });
    return replyJson(request_id, true, "get_identity_contract accepted", data);
  }
  if (command == "get_clinical_mainline_contract") {
    const auto runtime_cfg = sdk_robot_.runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object({
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("required_sequence", json::stringArray({"connect_robot", "power_on", "set_auto_mode", "lock_session", "load_scan_plan", "approach_prescan", "seek_contact", "start_scan", "safe_retreat"})),
        json::field("single_control_source_required", json::boolLiteral(identity.requires_single_control_source)),
        json::field("preferred_link", json::quote(identity.preferred_link)),
        json::field("rt_loop_hz", std::to_string(1000)),
        json::field("cartesian_impedance_limits", vectorJson(identity.cartesian_impedance_limits)),
        json::field("desired_wrench_limits", vectorJson(identity.desired_wrench_limits))
    });
    return replyJson(request_id, true, "get_clinical_mainline_contract accepted", data);
  }
  if (command == "get_session_drift_contract") {
    return replyJson(request_id, true, "get_session_drift_contract accepted", sessionDriftContractJsonLocked());
  }
  if (command == "get_hardware_lifecycle_contract") {
    return replyJson(request_id, true, "get_hardware_lifecycle_contract accepted", hardwareLifecycleContractJsonLocked());
  }
  if (command == "get_rt_kernel_contract") {
    return replyJson(request_id, true, "get_rt_kernel_contract accepted", rtKernelContractJsonLocked());
  }
  if (command == "get_session_freeze") {
    const auto data = json::object({
        json::field("session_locked", json::boolLiteral(!session_id_.empty())),
        json::field("session_id", json::quote(session_id_)),
        json::field("session_dir", json::quote(session_dir_)),
        json::field("locked_at_ns", std::to_string(session_locked_ts_ns_)),
        json::field("plan_hash", json::quote(plan_hash_)),
        json::field("active_segment", std::to_string(active_segment_)),
        json::field("tool_name", json::quote(config_.tool_name)),
        json::field("tcp_name", json::quote(config_.tcp_name)),
        json::field("load_kg", json::formatDouble(config_.load_kg)),
        json::field("rt_mode", json::quote(config_.rt_mode)),
        json::field("cartesian_impedance", vectorJson(config_.cartesian_impedance)),
        json::field("desired_wrench_n", vectorJson(config_.desired_wrench_n))
    });
    return replyJson(request_id, true, "get_session_freeze accepted", data);
  }
  if (command == "get_control_governance_contract") {
    return replyJson(request_id, true, "get_control_governance_contract accepted", controlGovernanceContractJsonLocked());
  }
  if (command == "get_controller_evidence") {
    return replyJson(request_id, true, "get_controller_evidence accepted", controllerEvidenceJsonLocked());
  }
  if (command == "get_dual_state_machine_contract") {
    return replyJson(request_id, true, "get_dual_state_machine_contract accepted", dualStateMachineContractJsonLocked());
  }
  if (command == "get_mainline_executor_contract") {
    return replyJson(request_id, true, "get_mainline_executor_contract accepted", mainlineExecutorContractJsonLocked());
  }
  if (command == "get_recovery_contract") {
    const auto data = json::object({
        json::field("collision_behavior", json::quote(config_.collision_behavior)),
        json::field("pause_resume_enabled", json::boolLiteral(true)),
        json::field("safe_retreat_enabled", json::boolLiteral(true)),
        json::field("resume_force_band_n", json::formatDouble(force_limits_.resume_force_band_n)),
        json::field("warning_z_force_n", json::formatDouble(force_limits_.warning_z_force_n)),
        json::field("max_z_force_n", json::formatDouble(force_limits_.max_z_force_n)),
        json::field("sensor_timeout_ms", json::formatDouble(force_limits_.sensor_timeout_ms)),
        json::field("stale_telemetry_ms", json::formatDouble(force_limits_.stale_telemetry_ms)),
        json::field("emergency_retract_mm", json::formatDouble(force_limits_.emergency_retract_mm))
    });
    return replyJson(request_id, true, "get_recovery_contract accepted", data);
  }
  if (command == "get_capability_contract") {
    return replyJson(request_id, true, "get_capability_contract accepted", capabilityContractJsonLocked());
  }
  if (command == "get_model_authority_contract") {
    return replyJson(request_id, true, "get_model_authority_contract accepted", modelAuthorityContractJsonLocked());
  }
  if (command == "get_release_contract") {
    return replyJson(request_id, true, "get_release_contract accepted", releaseContractJsonLocked());
  }
  if (command == "get_deployment_contract") {
    return replyJson(request_id, true, "get_deployment_contract accepted", deploymentContractJsonLocked());
  }
  if (command == "get_fault_injection_contract") {
    return replyJson(request_id, true, "get_fault_injection_contract accepted", faultInjectionContractJsonLocked());
  }
  if (command == "inject_fault") {
    const auto fault_name = json::extractString(line, "fault_name");
    std::string error_message;
    if (!applyFaultInjectionLocked(fault_name, &error_message)) {
      return replyJson(request_id, false, error_message.empty() ? "fault injection failed" : error_message);
    }
    return replyJson(request_id, true, "inject_fault accepted", faultInjectionContractJsonLocked());
  }
  if (command == "clear_injected_faults") {
    clearInjectedFaultsLocked();
    return replyJson(request_id, true, "clear_injected_faults accepted", faultInjectionContractJsonLocked());
  }
  if (command == "lock_session") {
    if (execution_state_ != RobotCoreState::AutoReady) {
      return replyJson(request_id, false, "core not ready for session lock");
    }
    session_id_ = json::extractString(line, "session_id");
    session_dir_ = json::extractString(line, "session_dir");
    if (session_id_.empty() || session_dir_.empty()) {
      return replyJson(request_id, false, "session_id or session_dir missing");
    }
    locked_scan_plan_hash_ = json::extractString(line, "scan_plan_hash");
    applyConfigFromJsonLocked(line);
    tool_ready_ = !config_.tool_name.empty();
    tcp_ready_ = !config_.tcp_name.empty();
    load_ready_ = config_.load_kg > 0.0;
    std::vector<std::string> session_blockers;
    std::vector<std::string> session_warnings;
    appendMainlineContractIssuesLocked(&session_blockers, &session_warnings);
    if (!session_blockers.empty()) {
      session_id_.clear();
      session_dir_.clear();
      locked_scan_plan_hash_.clear();
      return replyJson(request_id, false, session_blockers.front());
    }
    auto runtime_cfg = sdk_robot_.runtimeConfig();
    const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
    runtime_cfg.robot_model = identity.robot_model;
    runtime_cfg.sdk_robot_class = identity.sdk_robot_class;
    runtime_cfg.preferred_link = config_.preferred_link.empty() ? identity.preferred_link : config_.preferred_link;
    runtime_cfg.requires_single_control_source = config_.requires_single_control_source;
    runtime_cfg.clinical_mainline_mode = identity.clinical_mainline_mode;
    runtime_cfg.remote_ip = config_.remote_ip;
    runtime_cfg.local_ip = config_.local_ip;
    runtime_cfg.axis_count = identity.axis_count;
    runtime_cfg.rt_network_tolerance_percent = config_.rt_network_tolerance_percent;
    runtime_cfg.joint_filter_hz = config_.joint_filter_hz;
    runtime_cfg.cart_filter_hz = config_.cart_filter_hz;
    runtime_cfg.torque_filter_hz = config_.torque_filter_hz;
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.cartesian_impedance.size()); ++idx) runtime_cfg.cartesian_impedance[idx] = config_.cartesian_impedance[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.desired_wrench_n.size()); ++idx) runtime_cfg.desired_wrench_n[idx] = config_.desired_wrench_n[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, config_.fc_frame_matrix.size()); ++idx) runtime_cfg.fc_frame_matrix[idx] = config_.fc_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, config_.tcp_frame_matrix.size()); ++idx) runtime_cfg.tcp_frame_matrix[idx] = config_.tcp_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(3, config_.load_com_mm.size()); ++idx) runtime_cfg.load_com_mm[idx] = config_.load_com_mm[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.load_inertia.size()); ++idx) runtime_cfg.load_inertia[idx] = config_.load_inertia[idx];
    sdk_robot_.configureRtMainline(runtime_cfg);
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    sdk_robot_.setDragState(false, "cartesian", "admittance");
    std::filesystem::create_directories(session_dir_);
    recording_service_.openSession(session_dir_, session_id_);
    session_locked_ts_ns_ = json::nowNs();
    execution_state_ = RobotCoreState::SessionLocked;
    return replyJson(request_id, true, "lock_session accepted", json::object({json::field("session_id", json::quote(session_id_))}));
  }
  if (command == "load_scan_plan") {
    if (execution_state_ != RobotCoreState::SessionLocked && execution_state_ != RobotCoreState::PathValidated &&
        execution_state_ != RobotCoreState::ScanComplete) {
      return replyJson(request_id, false, "session not locked");
    }
    loadPlanFromJsonLocked(line);
    if (!plan_loaded_) {
      return replyJson(request_id, false, "scan plan missing segments");
    }
    if (!locked_scan_plan_hash_.empty() && !plan_hash_.empty() && locked_scan_plan_hash_ != plan_hash_) {
      plan_loaded_ = false;
      execution_state_ = RobotCoreState::SessionLocked;
      state_reason_ = "plan_hash_mismatch";
      return replyJson(request_id, false, "locked scan_plan_hash does not match loaded plan");
    }
    execution_state_ = RobotCoreState::PathValidated;
    state_reason_ = "scan_plan_validated";
    if (last_final_verdict_.plan_hash.empty() || last_final_verdict_.plan_hash == plan_hash_) {
      last_final_verdict_.accepted = true;
      last_final_verdict_.reason = "scan plan validated and loaded";
      last_final_verdict_.detail = "scan plan validated and loaded";
      last_final_verdict_.policy_state = "ready";
      last_final_verdict_.next_state = "approach_prescan";
      last_final_verdict_.plan_id = plan_id_;
      last_final_verdict_.plan_hash = plan_hash_;
      last_final_verdict_.summary_label = "模型前检通过";
    }
    return replyJson(request_id, true, "load_scan_plan accepted", json::object({json::field("plan_id", json::quote(plan_id_))}));
  }
  if (command == "approach_prescan") {
    if (execution_state_ != RobotCoreState::PathValidated) {
      return replyJson(request_id, false, "scan plan not ready");
    }
    nrt_motion_service_.approachPrescan();
    execution_state_ = RobotCoreState::Approaching;
    state_reason_ = "approach_prescan";
    contact_state_.recommended_action = "SEEK_CONTACT";
    return replyJson(request_id, true, "approach_prescan accepted");
  }
  if (command == "seek_contact") {
    std::string reason;
    if (!state_machine_guard_.allow(command, execution_state_, &reason)) {
      return replyJson(request_id, false, reason);
    }
    if (!rt_motion_service_.seekContact()) {
      return replyJson(request_id, false, "seek_contact failed");
    }
    execution_state_ = RobotCoreState::ContactSeeking;
    state_reason_ = "waiting_for_contact_stability";
    contact_state_.mode = "SEEKING_CONTACT";
    contact_state_.recommended_action = "WAIT_CONTACT_STABLE";
    return replyJson(request_id, true, "seek_contact accepted");
  }
  if (command == "start_scan") {
    std::string reason;
    if (!state_machine_guard_.allow(command, execution_state_, &reason)) {
      return replyJson(request_id, false, reason);
    }
    if (!rt_motion_service_.startCartesianImpedance()) {
      return replyJson(request_id, false, "start_scan failed");
    }
    execution_state_ = RobotCoreState::Scanning;
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, true);
    state_reason_ = "scan_active";
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.recommended_action = "SCAN";
    return replyJson(request_id, true, "start_scan accepted");
  }
  if (command == "pause_scan") {
    if (execution_state_ != RobotCoreState::Scanning) {
      return replyJson(request_id, false, "scan not active");
    }
    rt_motion_service_.pauseAndHold();
    recovery_manager_.pauseAndHold();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    execution_state_ = RobotCoreState::PausedHold;
    state_reason_ = "pause_hold";
    contact_state_.mode = "HOLDING_CONTACT";
    contact_state_.recommended_action = "RESUME_OR_RETREAT";
    return replyJson(request_id, true, "pause_scan accepted");
  }
  if (command == "resume_scan") {
    if (execution_state_ != RobotCoreState::PausedHold) {
      return replyJson(request_id, false, "scan not paused");
    }
    if (!rt_motion_service_.startCartesianImpedance()) {
      return replyJson(request_id, false, "resume_scan failed");
    }
    recovery_manager_.cancelRetry();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, true);
    execution_state_ = RobotCoreState::Scanning;
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, true);
    state_reason_ = "scan_active";
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.recommended_action = "SCAN";
    return replyJson(request_id, true, "resume_scan accepted");
  }
  if (command == "safe_retreat") {
    if (execution_state_ == RobotCoreState::Boot || execution_state_ == RobotCoreState::Disconnected || execution_state_ == RobotCoreState::Estop) {
      return replyJson(request_id, false, "cannot retreat from current state");
    }
    rt_motion_service_.controlledRetract();
    nrt_motion_service_.safeRetreat();
    recovery_manager_.controlledRetract();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    execution_state_ = RobotCoreState::Retreating;
    state_reason_ = "safe_retreat";
    retreat_ticks_remaining_ = 30;
    contact_state_.mode = "NO_CONTACT";
    contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
    return replyJson(request_id, true, "safe_retreat accepted");
  }
  if (command == "go_home") {
    nrt_motion_service_.goHome();
    return replyJson(request_id, true, "go_home accepted");
  }
  if (command == "clear_fault") {
    if (execution_state_ != RobotCoreState::Fault) {
      return replyJson(request_id, false, "no fault to clear");
    }
    fault_code_.clear();
    execution_state_ = plan_loaded_ ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
    return replyJson(request_id, true, "clear_fault accepted");
  }
  if (command == "emergency_stop") {
    rt_motion_service_.stop();
    recovery_manager_.cancelRetry();
    recovery_manager_.latchEstop();
    execution_state_ = RobotCoreState::Estop;
    fault_code_ = "ESTOP";
    queueAlarmLocked("FATAL_FAULT", "safety", "急停触发");
    return replyJson(request_id, true, "emergency_stop accepted");
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

TelemetrySnapshot CoreRuntime::takeTelemetrySnapshot() {
  std::lock_guard<std::mutex> lock(mutex_);
  TelemetrySnapshot snapshot;
  snapshot.core_state = buildCoreSnapshotLocked();
  snapshot.robot_state = robot_state_hub_.latest();
  snapshot.contact_state = contact_state_;
  snapshot.scan_progress = buildScanProgressLocked();
  snapshot.devices = devices_;
  snapshot.safety_status = evaluateSafetyLocked();
  snapshot.recorder_status = recording_service_.status();
  snapshot.quality_feedback = QualityFeedback{
      image_quality_,
      feature_confidence_,
      quality_score_,
      quality_score_ < 0.7,
  };
  snapshot.alarms = pending_alarms_;
  pending_alarms_.clear();
  return snapshot;
}

void CoreRuntime::rtStep() {
  std::lock_guard<std::mutex> lock(mutex_);
  phase_ += 0.03;
  ++frame_id_;
  updateQualityLocked();
  updateKinematicsLocked();
  updateContactAndProgressLocked();
  refreshDeviceHealthLocked(json::nowNs());
  recordStreamsLocked();
}

void CoreRuntime::statePollStep() {
  std::lock_guard<std::mutex> lock(mutex_);
  RobotStateSnapshot snapshot;
  snapshot.timestamp_ns = json::nowNs();
  snapshot.power_state = sdk_robot_.powered() ? "on" : "off";
  snapshot.operate_mode = sdk_robot_.automaticMode() ? "automatic" : "manual";
  snapshot.operation_state = stateName(execution_state_);
  snapshot.joint_pos = sdk_robot_.jointPos();
  snapshot.joint_vel = sdk_robot_.jointVel();
  snapshot.joint_torque = sdk_robot_.jointTorque();
  const double z_base = execution_state_ == RobotCoreState::Approaching
                            ? 220.0
                            : (execution_state_ == RobotCoreState::Retreating ? 230.0
                                                                               : (execution_state_ == RobotCoreState::ContactSeeking ||
                                                                                          execution_state_ == RobotCoreState::ContactStable ||
                                                                                          execution_state_ == RobotCoreState::Scanning ||
                                                                                          execution_state_ == RobotCoreState::PausedHold
                                                                                      ? 205.0
                                                                                      : 240.0));
  snapshot.tcp_pose = sdk_robot_.tcpPose();
  if (snapshot.tcp_pose.size() >= 6) {
    snapshot.tcp_pose[0] = 118.0 + 8.0 * std::sin(phase_ * 0.2);
    snapshot.tcp_pose[1] = 15.0 + 5.0 * std::cos(phase_ * 0.25);
    snapshot.tcp_pose[2] = z_base + 2.5 * std::sin(phase_ * 0.33);
  }
  snapshot.cart_force = {0.02, 0.01, pressure_current_, 0.0, 0.0, 0.0};
  snapshot.last_event = stateName(execution_state_);
  snapshot.last_controller_log = fault_code_.empty() ? "-" : fault_code_;
  robot_state_hub_.update(snapshot);
}

void CoreRuntime::watchdogStep() {
  std::lock_guard<std::mutex> lock(mutex_);
  const auto safety = evaluateSafetyLocked();
  const auto now = json::nowNs();
  const auto force_state = makeForceStateSnapshot(
      now,
      0.0,
      std::vector<double>{0.0, 0.0, pressure_current_, 0.0, 0.0, 0.0},
      force_limits_,
      config_.pressure_target);
  const auto decision = decideSafetyAction(force_state);
  const auto recovery_decision = recovery_policy_.evaluate(pressure_current_, config_.pressure_target, config_.pressure_upper, pressure_fresh_ ? 0.0 : static_cast<double>(config_.pressure_stale_ms));
  if (injected_faults_.count("rt_jitter_high") > 0) {
    rt_jitter_ok_ = false;
  }
  if (injected_faults_.count("pressure_stale") > 0) {
    pressure_fresh_ = false;
  }
  if (injected_faults_.count("overpressure") > 0 && execution_state_ == RobotCoreState::Scanning) {
    pressure_current_ = std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5);
  }
  if (decision == SafetyDecision::WarnOnly && execution_state_ == RobotCoreState::Scanning) {
    queueAlarmLocked("WARN", "force_monitor", "力控接近告警阈值", "force_monitor", "", "warn_only");
  }
  if (pressure_current_ > config_.pressure_upper && execution_state_ == RobotCoreState::Scanning) {
    rt_motion_service_.pauseAndHold();
    recovery_manager_.pauseAndHold();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    execution_state_ = RobotCoreState::PausedHold;
    contact_state_.mode = "OVERPRESSURE";
    contact_state_.recommended_action = "CONTROLLED_RETRACT";
    queueAlarmLocked("RECOVERABLE_FAULT", "contact", "压力超上限，已进入保持状态", "scan_monitor", "", "hold");
  }
  if (decision == SafetyDecision::ControlledRetract && execution_state_ != RobotCoreState::Estop) {
    rt_motion_service_.controlledRetract();
    recovery_manager_.controlledRetract();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    execution_state_ = RobotCoreState::Retreating;
    queueAlarmLocked("RECOVERABLE_FAULT", "force_monitor", "力控进入受控退让", "force_monitor", "", "controlled_retract");
  }
  if (decision == SafetyDecision::EstopLatch && execution_state_ != RobotCoreState::Estop) {
    recovery_manager_.latchEstop();
    execution_state_ = RobotCoreState::Estop;
    queueAlarmLocked("FATAL_FAULT", "force_monitor", "力传感器超时，进入急停锁存", "telemetry_watchdog", "", "estop");
  }
  if (execution_state_ == RobotCoreState::PausedHold || execution_state_ == RobotCoreState::Retreating) {
    const bool within_band = std::fabs(pressure_current_ - config_.pressure_target) <= force_limits_.resume_force_band_n;
    recovery_manager_.updateStableCondition(within_band, now);
  }
  if (!safety.safe_to_arm && controller_online_ && powered_ && automatic_mode_ && execution_state_ != RobotCoreState::Fault &&
      execution_state_ != RobotCoreState::Estop && !fault_code_.empty()) {
    queueAlarmLocked("WARN", "safety", "存在联锁，safe_to_arm 退化", "validate_setup", "", "warn_only");
  }
}

void CoreRuntime::updateKinematicsLocked() {
  if (execution_state_ == RobotCoreState::Retreating && retreat_ticks_remaining_ > 0) {
    --retreat_ticks_remaining_;
    if (retreat_ticks_remaining_ <= 0) {
      execution_state_ = plan_loaded_ ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
      contact_state_.recommended_action = "IDLE";
    }
  }
}

void CoreRuntime::updateQualityLocked() {
  image_quality_ = 0.78 + 0.12 * std::sin(phase_ * 0.7);
  feature_confidence_ = 0.74 + 0.10 * std::cos(phase_ * 0.45);
  quality_score_ = (image_quality_ + feature_confidence_) / 2.0;
}

void CoreRuntime::updateContactAndProgressLocked() {
  if (execution_state_ == RobotCoreState::ContactSeeking) {
    ContactObservationInput input;
    pressure_current_ = std::max(config_.pressure_lower, config_.pressure_target - 0.1 + 0.04 * std::sin(phase_));
    input.external_pressure = pressure_current_;
    input.cart_force_z = pressure_current_;
    input.quality_score = quality_score_;
    auto observed = contact_observer_.evaluate(input);
    if (pressure_current_ >= config_.pressure_target - 0.05) {
      if (contact_stable_since_ns_ <= 0) {
        contact_stable_since_ns_ = json::nowNs();
      }
      const auto gate = contact_gate_.evaluate(pressure_current_, config_.pressure_target, contact_stable_since_ns_, json::nowNs());
      contact_state_.mode = gate.mode;
      if (gate.contact_stable) {
        execution_state_ = RobotCoreState::ContactStable;
        state_reason_ = "contact_stable";
      }
    } else {
      contact_stable_since_ns_ = 0;
      contact_state_.mode = observed.mode;
    }
    contact_state_.confidence = 0.78;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = execution_state_ == RobotCoreState::ContactStable ? "START_SCAN" : "WAIT_CONTACT_STABLE";
    active_segment_ = std::max(active_segment_, 1);
    return;
  }
  if (execution_state_ == RobotCoreState::ContactStable) {
    pressure_current_ = injected_faults_.count("overpressure") > 0 ? std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5) : config_.pressure_target;
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.confidence = 0.83;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "START_SCAN";
    return;
  }
  if (execution_state_ == RobotCoreState::Scanning) {
    if (frame_id_ % 25 == 0) {
      ++path_index_;
    }
    if (total_points_ > 0) {
      progress_pct_ = std::min(100.0, 100.0 * static_cast<double>(path_index_) / static_cast<double>(total_points_));
      active_waypoint_index_ = std::min(total_points_, path_index_);
    }
    if (total_segments_ > 0) {
      const int points_per_segment = std::max(total_points_ / total_segments_, 1);
      active_segment_ = std::min(total_segments_, std::max(1, path_index_ / points_per_segment + 1));
    }
    sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
    pressure_current_ = injected_faults_.count("overpressure") > 0 ? std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5) : (config_.pressure_target + 0.08 * std::sin(phase_));
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.confidence = 0.87;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "SCAN";
    if (progress_pct_ >= 100.0) {
      sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
      execution_state_ = RobotCoreState::ScanComplete;
      contact_state_.mode = "NO_CONTACT";
      contact_state_.recommended_action = "POSTPROCESS";
    }
    return;
  }
  if (execution_state_ == RobotCoreState::PausedHold) {
    pressure_current_ = config_.pressure_target - 0.03;
    contact_state_.mode = "HOLDING_CONTACT";
    contact_state_.confidence = 0.75;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "RESUME_OR_RETREAT";
    return;
  }
  if (execution_state_ == RobotCoreState::Retreating) {
    pressure_current_ = 0.0;
    sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
    contact_state_.mode = "NO_CONTACT";
    contact_state_.confidence = 0.0;
    contact_state_.pressure_current = 0.0;
    contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
    return;
  }
  pressure_current_ = std::max(0.0, config_.pressure_target - 0.25);
  contact_stable_since_ns_ = 0;
  contact_state_.mode = "NO_CONTACT";
  contact_state_.confidence = 0.0;
  contact_state_.pressure_current = pressure_current_;
  contact_state_.recommended_action = "IDLE";
}

void CoreRuntime::refreshDeviceHealthLocked(int64_t ts_ns) {
  pressure_fresh_ = false;
  robot_state_fresh_ = false;
  for (auto& device : devices_) {
    device.fresh = device.online;
    device.last_ts_ns = device.online ? ts_ns : 0;
    if (device.device_name == "pressure" && device.online) {
      pressure_fresh_ = true;
    }
    if (device.device_name == "robot" && device.online) {
      robot_state_fresh_ = true;
    }
    if (device.device_name == "robot" && (execution_state_ == RobotCoreState::Fault || execution_state_ == RobotCoreState::Estop)) {
      device.detail = "机器人控制器处于故障或急停状态";
    }
  }
}

SafetyStatus CoreRuntime::evaluateSafetyLocked() const {
  auto status = safety_service_.evaluate(
      controller_online_,
      powered_,
      automatic_mode_,
      !session_id_.empty(),
      plan_loaded_,
      pressure_fresh_,
      robot_state_fresh_,
      pressure_current_ <= config_.pressure_upper,
      rt_jitter_ok_,
      tool_ready_,
      tcp_ready_,
      load_ready_);
  const auto recovery = recovery_policy_.evaluate(pressure_current_, config_.pressure_target, config_.pressure_upper, pressure_fresh_ ? 0.0 : static_cast<double>(config_.pressure_stale_ms));
  status.recovery_reason = recovery.reason;
  status.last_recovery_action = recovery.action;
  status.sensor_freshness_ms = pressure_fresh_ ? 0 : config_.pressure_stale_ms;
  status.pressure_band_state = std::fabs(pressure_current_ - config_.pressure_target) <= force_limits_.resume_force_band_n ? "WITHIN_RESUME_BAND" : "OUT_OF_BAND";
  return status;
}

void CoreRuntime::queueAlarmLocked(const std::string& severity, const std::string& source, const std::string& message, const std::string& workflow_step, const std::string& request_id, const std::string& auto_action) {
  AlarmEvent alarm;
  alarm.severity = severity;
  alarm.source = source;
  alarm.message = message;
  alarm.session_id = session_id_;
  alarm.segment_id = active_segment_;
  alarm.event_ts_ns = json::nowNs();
  alarm.workflow_step = workflow_step;
  alarm.request_id = request_id;
  alarm.auto_action = auto_action;
  pending_alarms_.push_back(alarm);
  recording_service_.recordAlarm(alarm);
  if (severity == "FATAL_FAULT") {
    fault_code_ = source;
    execution_state_ = execution_state_ == RobotCoreState::Estop ? RobotCoreState::Estop : RobotCoreState::Fault;
  }
}

CoreStateSnapshot CoreRuntime::buildCoreSnapshotLocked() const {
  CoreStateSnapshot snapshot;
  snapshot.execution_state = execution_state_;
  snapshot.armed = !session_id_.empty() && plan_loaded_ && execution_state_ != RobotCoreState::Fault && execution_state_ != RobotCoreState::Estop;
  snapshot.fault_code = fault_code_;
  snapshot.active_segment = active_segment_;
  snapshot.progress_pct = progress_pct_;
  snapshot.session_id = session_id_;
  snapshot.recovery_state = recovery_manager_.currentStateName();
  snapshot.plan_hash = plan_hash_;
  snapshot.contact_stable = execution_state_ == RobotCoreState::ContactStable || execution_state_ == RobotCoreState::Scanning || execution_state_ == RobotCoreState::PausedHold;
  snapshot.contact_stable_since_ns = contact_stable_since_ns_;
  snapshot.active_waypoint_index = active_waypoint_index_;
  snapshot.last_transition = last_transition_;
  snapshot.state_reason = state_reason_;
  return snapshot;
}

ScanProgress CoreRuntime::buildScanProgressLocked() const {
  ScanProgress progress;
  progress.active_segment = active_segment_;
  progress.path_index = path_index_;
  progress.overall_progress = progress_pct_;
  progress.frame_id = frame_id_;
  return progress;
}

void CoreRuntime::recordStreamsLocked() {
  if (!recording_service_.active()) {
    return;
  }
  recording_service_.recordRobotState(robot_state_hub_.latest());
  recording_service_.recordContactState(contact_state_);
  recording_service_.recordScanProgress(buildCoreSnapshotLocked(), buildScanProgressLocked());
}

void CoreRuntime::applyConfigFromJsonLocked(const std::string& json_line) {
  const auto config_json = json::extractObject(json_line, "config_snapshot", "{}");
  const auto& source = config_json != "{}" ? config_json : json_line;
  config_.pressure_target = json::extractDouble(source, "pressure_target", config_.pressure_target);
  config_.pressure_upper = json::extractDouble(source, "pressure_upper", config_.pressure_upper);
  config_.pressure_lower = json::extractDouble(source, "pressure_lower", config_.pressure_lower);
  config_.scan_speed_mm_s = json::extractDouble(source, "scan_speed_mm_s", config_.scan_speed_mm_s);
  config_.sample_step_mm = json::extractDouble(source, "sample_step_mm", config_.sample_step_mm);
  config_.segment_length_mm = json::extractDouble(source, "segment_length_mm", config_.segment_length_mm);
  config_.strip_width_mm = json::extractDouble(source, "strip_width_mm", config_.strip_width_mm);
  config_.strip_overlap_mm = json::extractDouble(source, "strip_overlap_mm", config_.strip_overlap_mm);
  config_.contact_seek_speed_mm_s = json::extractDouble(source, "contact_seek_speed_mm_s", config_.contact_seek_speed_mm_s);
  config_.retreat_speed_mm_s = json::extractDouble(source, "retreat_speed_mm_s", config_.retreat_speed_mm_s);
  config_.image_quality_threshold = json::extractDouble(source, "image_quality_threshold", config_.image_quality_threshold);
  config_.smoothing_factor = json::extractDouble(source, "smoothing_factor", config_.smoothing_factor);
  config_.reconstruction_step = json::extractDouble(source, "reconstruction_step", config_.reconstruction_step);
  config_.feature_threshold = json::extractDouble(source, "feature_threshold", config_.feature_threshold);
  config_.roi_mode = json::extractString(source, "roi_mode", config_.roi_mode);
  config_.network_stale_ms = json::extractInt(source, "network_stale_ms", config_.network_stale_ms);
  config_.pressure_stale_ms = json::extractInt(source, "pressure_stale_ms", config_.pressure_stale_ms);
  config_.telemetry_rate_hz = json::extractInt(source, "telemetry_rate_hz", config_.telemetry_rate_hz);
  config_.tool_name = json::extractString(source, "tool_name", config_.tool_name);
  config_.tcp_name = json::extractString(source, "tcp_name", config_.tcp_name);
  config_.load_kg = json::extractDouble(source, "load_kg", config_.load_kg);
  config_.rt_mode = json::extractString(source, "rt_mode", config_.rt_mode);
  config_.remote_ip = json::extractString(source, "remote_ip", config_.remote_ip);
  config_.local_ip = json::extractString(source, "local_ip", config_.local_ip);
  config_.force_sensor_provider = json::extractString(source, "force_sensor_provider", config_.force_sensor_provider);
  config_.robot_model = json::extractString(source, "robot_model", config_.robot_model);
  config_.axis_count = std::max(1, json::extractInt(source, "axis_count", config_.axis_count));
  config_.sdk_robot_class = json::extractString(source, "sdk_robot_class", config_.sdk_robot_class);
  config_.preferred_link = json::extractString(source, "preferred_link", config_.preferred_link);
  config_.requires_single_control_source = json::extractBool(source, "requires_single_control_source", config_.requires_single_control_source);
  config_.build_id = json::extractString(source, "build_id", config_.build_id);
  config_.software_version = json::extractString(source, "software_version", config_.software_version);
  config_.rt_network_tolerance_percent = json::extractInt(source, "rt_network_tolerance_percent", config_.rt_network_tolerance_percent);
  config_.joint_filter_hz = json::extractDouble(source, "joint_filter_hz", config_.joint_filter_hz);
  config_.cart_filter_hz = json::extractDouble(source, "cart_filter_hz", config_.cart_filter_hz);
  config_.torque_filter_hz = json::extractDouble(source, "torque_filter_hz", config_.torque_filter_hz);
  config_.collision_detection_enabled = json::extractBool(source, "collision_detection_enabled", config_.collision_detection_enabled);
  config_.collision_sensitivity = json::extractInt(source, "collision_sensitivity", config_.collision_sensitivity);
  config_.collision_behavior = json::extractString(source, "collision_behavior", config_.collision_behavior);
  config_.collision_fallback_mm = json::extractDouble(source, "collision_fallback_mm", config_.collision_fallback_mm);
  config_.soft_limit_enabled = json::extractBool(source, "soft_limit_enabled", config_.soft_limit_enabled);
  config_.joint_soft_limit_margin_deg = json::extractDouble(source, "joint_soft_limit_margin_deg", config_.joint_soft_limit_margin_deg);
  config_.singularity_avoidance_enabled = json::extractBool(source, "singularity_avoidance_enabled", config_.singularity_avoidance_enabled);
  config_.rl_project_name = json::extractString(source, "rl_project_name", config_.rl_project_name);
  config_.rl_task_name = json::extractString(source, "rl_task_name", config_.rl_task_name);
  config_.xpanel_vout_mode = json::extractString(source, "xpanel_vout_mode", config_.xpanel_vout_mode);
  config_.fc_frame_type = json::extractString(source, "fc_frame_type", config_.fc_frame_type);
  const auto cartesian_impedance = json::extractDoubleArray(source, "cartesian_impedance", config_.cartesian_impedance);
  if (!cartesian_impedance.empty()) config_.cartesian_impedance = cartesian_impedance;
  const auto desired_wrench_n = json::extractDoubleArray(source, "desired_wrench_n", config_.desired_wrench_n);
  if (!desired_wrench_n.empty()) config_.desired_wrench_n = desired_wrench_n;
  const auto fc_frame_matrix = json::extractDoubleArray(source, "fc_frame_matrix", config_.fc_frame_matrix);
  if (!fc_frame_matrix.empty()) config_.fc_frame_matrix = fc_frame_matrix;
  const auto tcp_frame_matrix = json::extractDoubleArray(source, "tcp_frame_matrix", config_.tcp_frame_matrix);
  if (!tcp_frame_matrix.empty()) config_.tcp_frame_matrix = tcp_frame_matrix;
  const auto load_com_mm = json::extractDoubleArray(source, "load_com_mm", config_.load_com_mm);
  if (!load_com_mm.empty()) config_.load_com_mm = load_com_mm;
  const auto load_inertia = json::extractDoubleArray(source, "load_inertia", config_.load_inertia);
  if (!load_inertia.empty()) config_.load_inertia = load_inertia;
}

void CoreRuntime::loadPlanFromJsonLocked(const std::string& json_line) {
  const auto plan = scan_plan_parser_.parseJsonEnvelope(json_line);
  std::string error;
  if (!scan_plan_validator_.validate(plan, &error)) {
    plan_loaded_ = false;
    state_reason_ = error;
    return;
  }
  plan_id_ = plan.plan_id;
  plan_hash_ = !plan.plan_hash.empty() ? plan.plan_hash : json::extractString(json_line, "scan_plan_hash");
  total_segments_ = static_cast<int>(plan.segments.size());
  total_points_ = std::max(total_segments_ * std::max(static_cast<int>(config_.segment_length_mm / std::max(config_.sample_step_mm, 0.1)), 2), 0);
  path_index_ = 0;
  active_waypoint_index_ = 0;
  progress_pct_ = 0.0;
  active_segment_ = total_segments_ > 0 ? plan.segments.front().segment_id : 0;
  sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
  plan_loaded_ = total_segments_ > 0;
}

FinalVerdict CoreRuntime::compileScanPlanVerdictLocked(const std::string& json_line) {
  applyConfigFromJsonLocked(json_line);
  const auto plan_json = json::extractObject(json_line, "scan_plan", "{}");
  auto plan = scan_plan_parser_.parseJsonEnvelope(plan_json == "{}" ? json_line : plan_json);
  if (plan.plan_hash.empty()) {
    plan.plan_hash = json::extractString(json_line, "scan_plan_hash", plan_hash_);
  }
  FinalVerdict verdict;
  verdict.source = "cpp_robot_core";
  verdict.plan_id = plan.plan_id;
  verdict.plan_hash = plan.plan_hash;
  verdict.evidence_id = std::string("cpp-final-verdict:") + (plan.plan_hash.empty() ? std::string("no-plan") : plan.plan_hash) + ":" + (session_id_.empty() ? std::string("unlocked") : session_id_);

  std::string error;
  if (!scan_plan_validator_.validate(plan, &error)) {
    verdict.accepted = false;
    verdict.reason = error;
    verdict.detail = error;
    verdict.policy_state = "blocked";
    verdict.summary_label = "模型前检阻塞";
    verdict.next_state = "replan_required";
    verdict.blockers.push_back(error);
    return verdict;
  }

  appendMainlineContractIssuesLocked(&verdict.blockers, &verdict.warnings);
  const auto safety = evaluateSafetyLocked();
  if (!safety.active_interlocks.empty()) {
    verdict.warnings.push_back("active interlocks present during compile");
  }
  if (!session_id_.empty() && !plan.session_id.empty() && plan.session_id != session_id_) {
    verdict.warnings.push_back("plan session_id differs from locked session");
  }
  if (!locked_scan_plan_hash_.empty() && !plan.plan_hash.empty() && locked_scan_plan_hash_ != plan.plan_hash) {
    verdict.blockers.push_back("plan_hash does not match locked session freeze");
  }
  if (plan.execution_constraints.max_segment_duration_ms == 0) {
    verdict.warnings.push_back("execution constraint max_segment_duration_ms not set");
  }

  verdict.accepted = verdict.blockers.empty();
  verdict.policy_state = verdict.accepted ? (verdict.warnings.empty() ? "ready" : "warning") : "blocked";
  verdict.summary_label = verdict.accepted ? (verdict.warnings.empty() ? "模型前检通过" : "模型前检告警") : "模型前检阻塞";
  verdict.next_state = verdict.accepted ? (session_id_.empty() ? "lock_session" : "load_scan_plan") : "replan_required";
  verdict.reason = verdict.accepted ? (verdict.warnings.empty() ? "scan plan compiled successfully" : "scan plan compiled with warnings") : verdict.blockers.front();
  verdict.detail = verdict.accepted ? (verdict.warnings.empty() ? "scan plan compiled successfully" : "scan plan compiled with warnings") : verdict.blockers.front();
  return verdict;
}


void CoreRuntime::appendMainlineContractIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings) const {
  const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  auto push_blocker = [&](const std::string& message) {
    if (blockers) blockers->push_back(message);
  };
  auto push_warning = [&](const std::string& message) {
    if (warnings) warnings->push_back(message);
  };
  if (config_.rt_mode != identity.clinical_mainline_mode) {
    push_blocker("clinical mainline requires " + identity.clinical_mainline_mode + " rt_mode");
  }
  if (std::find(identity.supported_rt_modes.begin(), identity.supported_rt_modes.end(), config_.rt_mode) == identity.supported_rt_modes.end()) {
    push_blocker("rt_mode is not supported by the resolved robot identity");
  }
  if (config_.rt_mode == "directTorque") {
    push_blocker("directTorque is forbidden in the clinical mainline");
  }
  if (config_.preferred_link != identity.preferred_link) {
    push_blocker("preferred_link deviates from official clinical mainline link");
  }
  if (!config_.requires_single_control_source || !identity.requires_single_control_source) {
    push_blocker("single control source must be locked before clinical execution");
  }
  if (config_.remote_ip.empty() || config_.local_ip.empty()) {
    push_blocker("remote_ip/local_ip must be configured for connectToRobot");
  }
  if (config_.sdk_robot_class != identity.sdk_robot_class || int(config_.axis_count) != int(identity.axis_count)) {
    push_blocker("robot identity does not match official clinical mainline");
  }
  if (config_.tool_name.empty()) {
    push_blocker("tool_name missing");
  }
  if (config_.tcp_name.empty()) {
    push_blocker("tcp_name missing");
  }
  if (config_.load_kg <= 0.0) {
    push_blocker("load_kg must be positive");
  }
  if (!vectorWithinLimits(config_.cartesian_impedance, identity.cartesian_impedance_limits)) {
    push_blocker("cartesian_impedance exceeds official limits");
  }
  if (!vectorWithinLimits(config_.desired_wrench_n, identity.desired_wrench_limits)) {
    push_blocker("desired_wrench_n exceeds official limits");
  }
  if (config_.joint_filter_hz < identity.joint_filter_range_hz.front() || config_.joint_filter_hz > identity.joint_filter_range_hz.back() ||
      config_.cart_filter_hz < identity.joint_filter_range_hz.front() || config_.cart_filter_hz > identity.joint_filter_range_hz.back() ||
      config_.torque_filter_hz < identity.joint_filter_range_hz.front() || config_.torque_filter_hz > identity.joint_filter_range_hz.back()) {
    push_blocker("filter cutoff frequency out of official range");
  }
  if (config_.rt_network_tolerance_percent < identity.rt_network_tolerance_range.front() || config_.rt_network_tolerance_percent > identity.rt_network_tolerance_range.back()) {
    push_blocker("rt_network_tolerance_percent out of official range");
  } else if (config_.rt_network_tolerance_percent < identity.rt_network_tolerance_recommended.front() || config_.rt_network_tolerance_percent > identity.rt_network_tolerance_recommended.back()) {
    push_warning("rt_network_tolerance_percent outside recommended range");
  }
  if (!config_.collision_detection_enabled) {
    push_blocker("collision detection must stay enabled in the clinical mainline");
  }
  if (!config_.soft_limit_enabled) {
    push_blocker("soft limit must stay enabled in the clinical mainline");
  }
  if (!config_.singularity_avoidance_enabled) {
    push_warning("singularity avoidance is disabled");
  }
  if (!sdk_robot_.sdkAvailable()) {
    push_warning("vendored xCore SDK is not linked; runtime remains contract-simulated");
  }
  if (!sdk_robot_.xmateModelAvailable()) {
    push_warning("xMateModel is unavailable; model authority is degraded");
  }
}

bool CoreRuntime::sessionFreezeConsistentLocked() const {
  if (session_id_.empty() || session_dir_.empty()) {
    return false;
  }
  if (!(tool_ready_ && tcp_ready_ && load_ready_)) {
    return false;
  }
  if (!locked_scan_plan_hash_.empty() && !plan_hash_.empty() && locked_scan_plan_hash_ != plan_hash_) {
    return false;
  }
  return true;
}

std::string CoreRuntime::capabilityContractJsonLocked() const {
  const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  using namespace json;
  std::vector<std::string> modules;
  modules.push_back(object({field("module", quote("rokae::Robot")), field("enabled", boolLiteral(true)), field("status", quote("ready")), field("purpose", quote("连接、上电、模式切换、姿态/关节/日志/工具工件查询"))}));
  modules.push_back(object({field("module", quote("rokae::RtMotionControl")), field("enabled", boolLiteral(config_.rt_mode == identity.clinical_mainline_mode && config_.rt_mode != "directTorque")), field("status", quote(config_.rt_mode == identity.clinical_mainline_mode && config_.rt_mode != "directTorque" ? "ready" : "policy_blocked")), field("purpose", quote("1 kHz 实时阻抗/位置控制主线"))}));
  modules.push_back(object({field("module", quote("rokae::Planner")), field("enabled", boolLiteral(identity.supports_planner)), field("status", quote(identity.supports_planner ? "ready" : "unsupported")), field("purpose", quote("S 曲线/点位跟随的上位机路径规划"))}));
  modules.push_back(object({field("module", quote("rokae::xMateModel")), field("enabled", boolLiteral(identity.supports_xmate_model)), field("status", quote(identity.supports_xmate_model ? (sdk_robot_.xmateModelAvailable() ? "ready" : "degraded") : "unsupported")), field("purpose", quote("正逆解、雅可比、动力学前向计算"))}));
  modules.push_back(object({field("module", quote("通信 I/O")), field("enabled", boolLiteral(true)), field("status", quote("ready")), field("purpose", quote("DI/DO/AI/AO、寄存器、xPanel 供电配置"))}));
  modules.push_back(object({field("module", quote("RL 工程")), field("enabled", boolLiteral(true)), field("status", quote("ready")), field("purpose", quote("projectsInfo / loadProject / runProject / pauseProject"))}));
  modules.push_back(object({field("module", quote("协作功能")), field("enabled", boolLiteral(identity.supports_drag || identity.supports_path_replay)), field("status", quote(identity.supports_drag || identity.supports_path_replay ? "ready" : "unsupported")), field("purpose", quote("拖动示教、路径录制/回放、奇异规避"))}));
  std::vector<std::string> blockers; std::vector<std::string> warnings; appendMainlineContractIssuesLocked(&blockers, &warnings);
  return object({
      field("robot_model", quote(identity.robot_model)),
      field("sdk_robot_class", quote(identity.sdk_robot_class)),
      field("controller_version", quote(identity.controller_version)),
      field("preferred_link", quote(config_.preferred_link)),
      field("rt_loop_hz", std::to_string(1000)),
      field("scan_rt_mode", quote(config_.rt_mode)),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("modules", objectArray(modules)),
      field("blockers", objectArray([&](){ std::vector<std::string> items; for (const auto& b: blockers) items.push_back(summaryEntry("capability", b)); return items; }())),
      field("warnings", objectArray([&](){ std::vector<std::string> items; for (const auto& w: warnings) items.push_back(summaryEntry("capability", w)); return items; }())),
      field("clinical_policy", object({field("mainline_scan_mode", quote(identity.clinical_mainline_mode)), field("direct_torque_allowed", boolLiteral(false)), field("single_control_source_required", boolLiteral(identity.requires_single_control_source))}))
  });
}

std::string CoreRuntime::modelAuthorityContractJsonLocked() const {
  const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  using namespace json;
  const bool authoritative_precheck = sdk_robot_.sdkAvailable() && sdk_robot_.xmateModelAvailable() && identity.supports_xmate_model;
  std::vector<std::string> warnings;
  if (!sdk_robot_.sdkAvailable()) warnings.push_back(summaryEntry("model_authority", "vendored xCore SDK is not linked; authoritative runtime is unavailable"));
  if (!sdk_robot_.xmateModelAvailable()) warnings.push_back(summaryEntry("model_authority", "xMateModel library is unavailable; planner/model authority is degraded"));
  return object({
      field("authoritative_kernel", quote("cpp_robot_core")),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("robot_model", quote(identity.robot_model)),
      field("sdk_robot_class", quote(identity.sdk_robot_class)),
      field("planner_supported", boolLiteral(identity.supports_planner)),
      field("xmate_model_supported", boolLiteral(identity.supports_xmate_model)),
      field("authoritative_precheck", boolLiteral(authoritative_precheck)),
      field("approximate_advisory_allowed", boolLiteral(true)),
      field("planner_primitives", stringArray({"JointMotionGenerator", "CartMotionGenerator", "FollowPosition"})),
      field("model_methods", stringArray({"robot.model()", "getCartPose", "getJointPos", "jacobian", "getTorque"})),
      field("warnings", objectArray(warnings))
  });
}

std::string CoreRuntime::hardwareLifecycleContractJsonLocked() const {
  using namespace json;
  const std::string lifecycle = sdk_robot_.hardwareLifecycleState();
  const bool live_takeover_ready = sdk_robot_.sdkAvailable() && controller_online_ && powered_ && automatic_mode_ && sdk_robot_.rtMainlineConfigured();
  const std::string summary_state = live_takeover_ready ? "ready" : (controller_online_ ? "warning" : "blocked");
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(live_takeover_ready ? std::string("hardware lifecycle ready") : std::string("hardware lifecycle contract"))),
      field("detail", quote("Hardware layer owns SDK channels and exposes read/update/write style lifecycle readiness.")),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("sdk_binding_mode", quote(sdk_robot_.sdkBindingMode())),
      field("lifecycle_state", quote(lifecycle)),
      field("controller_manager_model", quote("hardware_layer__read_update_write")),
      field("transport_ready", boolLiteral(controller_online_)),
      field("motion_channel_ready", boolLiteral(sdk_robot_.motionChannelReady())),
      field("state_channel_ready", boolLiteral(sdk_robot_.stateChannelReady())),
      field("aux_channel_ready", boolLiteral(sdk_robot_.auxChannelReady())),
      field("live_takeover_ready", boolLiteral(live_takeover_ready)),
      field("single_control_source_required", boolLiteral(config_.requires_single_control_source))
  });
}

std::string CoreRuntime::rtKernelContractJsonLocked() const {
  using namespace json;
  const auto rt = rt_motion_service_.snapshot();
  const std::string summary_state = rt.degraded_without_sdk ? "warning" : "ready";
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(rt.degraded_without_sdk ? std::string("rt kernel contract only") : std::string("rt kernel ready"))),
      field("detail", quote("RT kernel follows read/update/write staging around the official SDK controller callback.")),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("nominal_loop_hz", std::to_string(rt.nominal_loop_hz)),
      field("read_update_write", stringArray({"read_state", "update_phase_policy", "write_command"})),
      field("phase", quote(rt.phase)),
      field("monitors", object({
          field("reference_limiter", boolLiteral(rt.reference_limiter_enabled)),
          field("freshness_guard", boolLiteral(rt.freshness_guard_enabled)),
          field("jitter_monitor", boolLiteral(rt.jitter_monitor_enabled)),
          field("contact_band_monitor", boolLiteral(rt.contact_band_monitor_enabled))
      })),
      field("jitter_budget_ms", formatDouble(0.2)),
      field("freshness_budget_ms", std::to_string(config_.pressure_stale_ms)),
      field("reference_limits", object({field("max_cart_step_mm", formatDouble(2.5)), field("max_force_delta_n", formatDouble(1.0))})),
      field("degraded_without_sdk", boolLiteral(rt.degraded_without_sdk))
  });
}

std::string CoreRuntime::sessionDriftContractJsonLocked() const {
  using namespace json;
  const bool session_locked = !session_id_.empty();
  const bool freeze_consistent = sessionFreezeConsistentLocked();
  std::vector<std::string> drifts;
  if (session_locked && !freeze_consistent) {
    drifts.push_back(object({field("name", quote("plan_hash")), field("detail", quote("locked plan hash does not match active plan hash"))}));
  }
  return object({
      field("summary_state", quote(drifts.empty() ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(drifts.empty() ? std::string("hard freeze consistent") : std::string("hard freeze drift detected"))),
      field("detail", quote("Session hard freeze watches runtime binding and locked plan hash consistency.")),
      field("session_locked", boolLiteral(session_locked)),
      field("locked_runtime_config_hash", quote(session_locked ? std::string("locked_by_runtime_contract") : std::string(""))),
      field("active_runtime_config_hash", quote(session_locked ? std::string("active_runtime_contract") : std::string(""))),
      field("locked_sdk_boundary_hash", quote(session_locked ? std::string("locked_sdk_boundary_contract") : std::string(""))),
      field("active_sdk_boundary_hash", quote(session_locked ? std::string("active_sdk_boundary_contract") : std::string(""))),
      field("locked_executor_hash", quote(session_locked ? std::string("locked_executor_contract") : std::string(""))),
      field("active_executor_hash", quote(session_locked ? std::string("active_executor_contract") : std::string(""))),
      field("locked_scan_plan_hash", quote(locked_scan_plan_hash_)),
      field("active_plan_hash", quote(plan_hash_)),
      field("drifts", objectArray(drifts))
  });
}

std::string CoreRuntime::controlGovernanceContractJsonLocked() const {
  using namespace json;
  const bool session_locked = !session_id_.empty();
  const bool session_binding_valid = sessionFreezeConsistentLocked();
  const bool rt_ready = controller_online_ && powered_ && automatic_mode_ && config_.rt_mode == "cartesianImpedance";
  const auto rt_snapshot = rt_motion_service_.snapshot();
  const auto nrt_snapshot = nrt_motion_service_.snapshot();
  return object({
      field("single_control_source_required", boolLiteral(config_.requires_single_control_source)),
      field("control_authority_expected_source", quote("cpp_robot_core")),
      field("write_surface", quote("core_runtime_only")),
      field("current_execution_state", quote(stateName(execution_state_))),
      field("controller_online", boolLiteral(controller_online_)),
      field("powered", boolLiteral(powered_)),
      field("automatic_mode", boolLiteral(automatic_mode_)),
      field("session_binding_valid", boolLiteral(session_binding_valid)),
      field("runtime_config_bound", boolLiteral(session_locked)),
      field("session_id", quote(session_id_)),
      field("active_plan_hash", quote(plan_hash_)),
      field("locked_scan_plan_hash", quote(locked_scan_plan_hash_)),
      field("tool_ready", boolLiteral(tool_ready_)),
      field("tcp_ready", boolLiteral(tcp_ready_)),
      field("load_ready", boolLiteral(load_ready_)),
      field("nrt_ready", boolLiteral(controller_online_ && powered_)),
      field("rt_ready", boolLiteral(rt_ready)),
      field("lifecycle_state", quote(sdk_robot_.hardwareLifecycleState())),
      field("rt_loop_active", boolLiteral(rt_snapshot.loop_active)),
      field("rt_move_active", boolLiteral(rt_snapshot.move_active)),
      field("nrt_last_command", quote(nrt_snapshot.last_command)),
      field("detail", quote("single control source contract requires session freeze + AUTO + powered + cartesianImpedance mainline"))
  });
}

std::string CoreRuntime::controllerEvidenceJsonLocked() const {
  using namespace json;
  const auto logs = sdk_robot_.controllerLogs();
  const auto cfg_logs = sdk_robot_.configurationLog();
  std::vector<std::string> log_tail;
  for (const auto& item : logs) {
    log_tail.push_back(object({field("level", quote("INFO")), field("source", quote("sdk")), field("message", quote(item))}));
  }
  std::vector<std::string> cfg_tail;
  for (const auto& item : cfg_logs) {
    cfg_tail.push_back(quote(item));
  }
  const auto rl_status = sdk_robot_.rlStatus();
  const auto drag = sdk_robot_.dragState();
  return object({
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("last_event", quote(stateName(execution_state_))),
      field("last_transition", quote(last_transition_)),
      field("state_reason", quote(state_reason_)),
      field("last_controller_log", quote(logs.empty() ? std::string("") : logs.back())),
      field("controller_log_tail", objectArray(log_tail)),
      field("configuration_log_tail", stringArray(cfg_logs)),
      field("rl_status", object({field("loaded_project", quote(rl_status.loaded_project)), field("loaded_task", quote(rl_status.loaded_task)), field("running", boolLiteral(rl_status.running)), field("rate", formatDouble(rl_status.rate)), field("loop", boolLiteral(rl_status.loop))})),
      field("drag_state", object({field("enabled", boolLiteral(drag.enabled)), field("space", quote(drag.space)), field("type", quote(drag.type))})),
      field("registers", object({field("segment", std::to_string(active_segment_)), field("frame", std::to_string(frame_id_))})),
      field("fault_code", quote(fault_code_)),
      field("pending_alarm_count", std::to_string(static_cast<int>(pending_alarms_.size()))),
      field("last_nrt_profile", quote(nrt_motion_service_.snapshot().active_profile)),
      field("last_rt_phase", quote(rt_motion_service_.snapshot().phase)),
      field("reason_chain", stringArray({stateName(execution_state_), state_reason_, last_transition_, fault_code_}))
  });
}


std::string CoreRuntime::dualStateMachineContractJsonLocked() const {
  using namespace json;
  const std::string runtime_state = stateName(execution_state_);
  std::string clinical_state = "boot";
  if (runtime_state == "CONNECTED" || runtime_state == "POWERED" || runtime_state == "AUTO_READY") clinical_state = "startup";
  else if (runtime_state == "SESSION_LOCKED") clinical_state = "session_locked";
  else if (runtime_state == "PATH_VALIDATED") clinical_state = "plan_validated";
  else if (runtime_state == "APPROACHING") clinical_state = "approaching";
  else if (runtime_state == "CONTACT_SEEKING") clinical_state = "seek_contact";
  else if (runtime_state == "CONTACT_STABLE") clinical_state = "contact_stable";
  else if (runtime_state == "SCANNING") clinical_state = "scan_follow";
  else if (runtime_state == "PAUSED_HOLD") clinical_state = "paused_hold";
  else if (runtime_state == "RETREATING" || runtime_state == "RECOVERY_RETRACT") clinical_state = "controlled_retract";
  else if (runtime_state == "SCAN_COMPLETE") clinical_state = "completed";
  else if (runtime_state == "FAULT") clinical_state = "fault";
  else if (runtime_state == "ESTOP") clinical_state = "estop";
  const bool aligned = !(runtime_state == "SCANNING" && clinical_state != "scan_follow");
  return object({
      field("summary_state", quote(aligned ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(aligned ? std::string("双层状态机已对齐") : std::string("双层状态机冲突"))),
      field("detail", quote(aligned ? std::string("执行状态机与临床任务状态机已通过映射规则对齐。") : std::string("runtime 与 clinical task state 不一致。"))),
      field("runtime_state", quote(runtime_state)),
      field("clinical_task_state", quote(clinical_state)),
      field("execution_and_clinical_aligned", boolLiteral(aligned)),
      field("execution_permissions", object({
          field("allow_nrt", boolLiteral(execution_state_ == RobotCoreState::AutoReady || execution_state_ == RobotCoreState::SessionLocked || execution_state_ == RobotCoreState::PathValidated || execution_state_ == RobotCoreState::ScanComplete)),
          field("allow_rt_seek", boolLiteral(execution_state_ == RobotCoreState::PathValidated || execution_state_ == RobotCoreState::Approaching || execution_state_ == RobotCoreState::ContactSeeking)),
          field("allow_rt_scan", boolLiteral(execution_state_ == RobotCoreState::ContactStable || execution_state_ == RobotCoreState::Scanning || execution_state_ == RobotCoreState::PausedHold)),
          field("allow_retract", boolLiteral(execution_state_ != RobotCoreState::Boot && execution_state_ != RobotCoreState::Disconnected && execution_state_ != RobotCoreState::Estop))
      }))
  });
}

std::string CoreRuntime::mainlineExecutorContractJsonLocked() const {
  using namespace json;
  const auto rt = rt_motion_service_.snapshot();
  const auto nrt = nrt_motion_service_.snapshot();
  std::vector<std::string> templates;
  for (const auto& profile : nrt.blocking_profiles) {
    templates.push_back(object({field("name", quote(profile)), field("blocking", boolLiteral(true)), field("delegates_to_sdk", boolLiteral(true))}));
  }
  const bool task_tree_aligned = !(stateName(execution_state_) == "SCANNING" && rt.phase != "scan_follow");
  return object({
      field("summary_state", quote(task_tree_aligned ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(task_tree_aligned ? std::string("主线执行器已对齐") : std::string("主线执行器未对齐"))),
      field("detail", quote("NRT/RT executor 只表达意图、阶段与监测器；真实执行委托给官方 SDK。")),
      field("task_tree_aligned", boolLiteral(task_tree_aligned)),
      field("nrt_executor", object({
          field("summary_state", quote(nrt.degraded_without_sdk ? std::string("warning") : std::string("ready"))),
          field("detail", quote("NRT executor delegates MoveAbsJ/MoveL templates to the official SDK planner.")),
          field("sdk_delegation_only", boolLiteral(nrt.sdk_delegation_only)),
          field("last_command_id", quote(nrt.last_command_id)),
          field("templates", objectArray(templates))
      })),
      field("rt_executor", object({
          field("summary_state", quote(rt.degraded_without_sdk ? std::string("warning") : std::string("ready"))),
          field("detail", quote("RT executor wraps cartesianImpedance mainline with limiter/guard semantics.")),
          field("phase", quote(rt.phase)),
          field("phase_group", quote(rt.phase_group)),
          field("reference_limiter_enabled", boolLiteral(rt.reference_limiter_enabled)),
          field("freshness_guard_enabled", boolLiteral(rt.freshness_guard_enabled)),
          field("jitter_monitor_enabled", boolLiteral(rt.jitter_monitor_enabled)),
          field("contact_band_monitor_enabled", boolLiteral(rt.contact_band_monitor_enabled)),
          field("nominal_loop_hz", std::to_string(rt.nominal_loop_hz))
      }))
  });
}

std::string CoreRuntime::releaseContractJsonLocked() const {
  using namespace json;
  const auto safety = evaluateSafetyLocked();
  const bool freeze_consistent = sessionFreezeConsistentLocked();
  const bool compile_ready = last_final_verdict_.accepted && freeze_consistent;
  std::vector<std::string> blockers; std::vector<std::string> warnings; appendMainlineContractIssuesLocked(&blockers, &warnings);
  for (const auto& item : last_final_verdict_.blockers) blockers.push_back(item);
  for (const auto& item : last_final_verdict_.warnings) warnings.push_back(item);
  const bool release_allowed = compile_ready && safety.active_interlocks.empty();
  return object({
      field("summary_state", quote(release_allowed ? std::string("ready") : std::string("blocked"))),
      field("session_locked", boolLiteral(!session_id_.empty())),
      field("session_freeze_consistent", boolLiteral(freeze_consistent)),
      field("locked_scan_plan_hash", quote(locked_scan_plan_hash_)),
      field("active_plan_hash", quote(plan_hash_)),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("compile_ready", boolLiteral(compile_ready)),
      field("ready_for_approach", boolLiteral(compile_ready && execution_state_ == RobotCoreState::PathValidated)),
      field("ready_for_scan", boolLiteral(compile_ready && execution_state_ == RobotCoreState::ContactStable)),
      field("release_recommendation", quote(release_allowed ? std::string("allow") : std::string("block"))),
      field("active_interlocks", stringArray(safety.active_interlocks)),
      field("final_verdict", object({field("accepted", boolLiteral(last_final_verdict_.accepted)), field("policy_state", quote(last_final_verdict_.policy_state)), field("reason", quote(last_final_verdict_.reason)), field("evidence_id", quote(last_final_verdict_.evidence_id))})),
      field("blockers", objectArray([&](){ std::vector<std::string> items; for (const auto& b: blockers) items.push_back(summaryEntry("release", b)); return items; }())),
      field("warnings", objectArray([&](){ std::vector<std::string> items; for (const auto& w: warnings) items.push_back(summaryEntry("release", w)); return items; }())),
      field("active_injections", stringArray([&](){ std::vector<std::string> items(injected_faults_.begin(), injected_faults_.end()); return items; }()))
  });
}

std::string CoreRuntime::deploymentContractJsonLocked() const {
  using namespace json;
  const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  return object({
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("vendored_sdk_required", boolLiteral(true)),
      field("vendored_sdk_detected", boolLiteral(sdk_robot_.sdkAvailable())),
      field("xmate_model_detected", boolLiteral(sdk_robot_.xmateModelAvailable())),
      field("preferred_link", quote(identity.preferred_link)),
      field("single_control_source_required", boolLiteral(identity.requires_single_control_source)),
      field("required_host_dependencies", stringArray({"cmake", "g++/clang++", "protobuf headers", "protoc", "openssl headers"})),
      field("required_runtime_materials", stringArray({"configs/tls/runtime/*", "vendored librokae include/lib/external"})),
      field("bringup_sequence", stringArray({"doctor_runtime.py", "generate_dev_tls_cert.sh", "start_real.sh", "run.py --backend core"})),
      field("systemd_units", stringArray({"spine-cpp-core.service", "spine-python-api.service", "spine-web-kiosk.service", "spine-ultrasound.target"})),
      field("summary_label", quote("cpp deployment contract"))
  });
}

std::string CoreRuntime::faultInjectionContractJsonLocked() const {
  using namespace json;
  const std::vector<std::string> catalog{
      object({field("name", quote("pressure_stale")), field("effect", quote("forces stale telemetry watchdog and estop path")), field("phase_scope", stringArray({"CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"})), field("recoverable", boolLiteral(false))}),
      object({field("name", quote("rt_jitter_high")), field("effect", quote("marks RT jitter interlock active")), field("phase_scope", stringArray({"CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("overpressure")), field("effect", quote("forces pressure above upper bound and pause/retreat logic")), field("phase_scope", stringArray({"CONTACT_STABLE", "SCANNING"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("collision_event")), field("effect", quote("injects recoverable collision alarm and retreat")), field("phase_scope", stringArray({"APPROACHING", "CONTACT_SEEKING", "SCANNING"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("plan_hash_mismatch")), field("effect", quote("breaks locked plan hash consistency")), field("phase_scope", stringArray({"SESSION_LOCKED", "PATH_VALIDATED"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("estop_latch")), field("effect", quote("forces ESTOP latched state")), field("phase_scope", stringArray({"*"})), field("recoverable", boolLiteral(false))}),
  };
  return object({
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("enabled", boolLiteral(true)),
      field("simulation_only", boolLiteral(true)),
      field("active_injections", stringArray([&](){ std::vector<std::string> items(injected_faults_.begin(), injected_faults_.end()); return items; }())),
      field("catalog", objectArray(catalog))
  });
}

bool CoreRuntime::applyFaultInjectionLocked(const std::string& fault_name, std::string* error_message) {
  if (fault_name.empty()) {
    if (error_message != nullptr) {
      *error_message = "fault_name missing";
    }
    return false;
  }

  injected_faults_.insert(fault_name);
  if (fault_name == "pressure_stale") {
    pressure_fresh_ = false;
    devices_[2].fresh = false;
    queueAlarmLocked("FAULT", "fault_injection", "压力遥测已被注入为 stale", "fault_injection");
    return true;
  }
  if (fault_name == "rt_jitter_high") {
    rt_jitter_ok_ = false;
    queueAlarmLocked("WARNING", "fault_injection", "RT jitter interlock injected", "fault_injection");
    return true;
  }
  if (fault_name == "overpressure") {
    pressure_current_ = std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5);
    queueAlarmLocked("WARNING", "fault_injection", "Overpressure injected", "fault_injection", "", "safe_retreat");
    return true;
  }
  if (fault_name == "collision_event") {
    execution_state_ = RobotCoreState::Retreating;
    retreat_ticks_remaining_ = std::max(retreat_ticks_remaining_, 10);
    queueAlarmLocked("RECOVERABLE_FAULT", "collision", "模拟碰撞事件", "fault_injection", "", "safe_retreat");
    return true;
  }
  if (fault_name == "plan_hash_mismatch") {
    plan_hash_ = std::string("mismatch:") + (plan_hash_.empty() ? "empty" : plan_hash_);
    return true;
  }
  if (fault_name == "estop_latch") {
    execution_state_ = RobotCoreState::Estop;
    fault_code_ = "ESTOP_INJECTED";
    queueAlarmLocked("FAULT", "fault_injection", "ESTOP latched by fault injection", "fault_injection");
    return true;
  }

  injected_faults_.erase(fault_name);
  if (error_message != nullptr) {
    *error_message = std::string("unsupported fault injection: ") + fault_name;
  }
  return false;
}

void CoreRuntime::clearInjectedFaultsLocked() {
  injected_faults_.clear();
  rt_jitter_ok_ = true;
  pressure_fresh_ = true;
  devices_[2].fresh = devices_[2].online;
  if (execution_state_ == RobotCoreState::Estop && fault_code_ == "ESTOP_INJECTED") {
    if (automatic_mode_ && powered_) {
      execution_state_ = RobotCoreState::AutoReady;
    } else if (powered_) {
      execution_state_ = RobotCoreState::Powered;
    } else if (controller_online_) {
      execution_state_ = RobotCoreState::Connected;
    } else {
      execution_state_ = RobotCoreState::Disconnected;
    }
    fault_code_.clear();
  }
  queueAlarmLocked("INFO", "fault_injection", "fault injections cleared", "fault_injection");
}

std::string CoreRuntime::finalVerdictJson(const FinalVerdict& verdict) const {
  using namespace json;
  std::vector<std::string> blocker_entries;
  blocker_entries.reserve(verdict.blockers.size());
  for (const auto& item : verdict.blockers) {
    blocker_entries.push_back(summaryEntry("model_precheck", item));
  }
  std::vector<std::string> warning_entries;
  warning_entries.reserve(verdict.warnings.size());
  for (const auto& item : verdict.warnings) {
    warning_entries.push_back(summaryEntry("model_precheck", item));
  }
  return object({
      field("summary_state", quote(verdict.policy_state.empty() ? std::string("idle") : verdict.policy_state)),
      field("summary_label", quote(verdict.summary_label.empty() ? std::string("运行时前检") : verdict.summary_label)),
      field("detail", quote(verdict.detail.empty() ? verdict.reason : verdict.detail)),
      field("warnings", objectArray(warning_entries)),
      field("blockers", objectArray(blocker_entries)),
      field("authority_source", quote(verdict.source.empty() ? std::string("cpp_robot_core") : verdict.source)),
      field("verdict_kind", quote("final")),
      field("approximate", boolLiteral(false)),
      field("final_verdict", object({
          field("accepted", boolLiteral(verdict.accepted)),
          field("reason", quote(verdict.reason)),
          field("evidence_id", quote(verdict.evidence_id)),
          field("expected_state_delta", object({field("next_state", quote(verdict.next_state.empty() ? std::string("replan_required") : verdict.next_state))})),
          field("policy_state", quote(verdict.policy_state.empty() ? std::string("idle") : verdict.policy_state)),
          field("source", quote(verdict.source.empty() ? std::string("cpp_robot_core") : verdict.source)),
          field("advisory_only", boolLiteral(verdict.advisory_only)),
      })),
      field("plan_metrics", object({
          field("plan_id", quote(verdict.plan_id)),
          field("plan_hash", quote(verdict.plan_hash)),
      })),
  });
}

std::string CoreRuntime::replyJson(const std::string& request_id, bool ok, const std::string& message, const std::string& data_json) const {
  using namespace json;
  return object({
      field("ok", boolLiteral(ok)),
      field("message", quote(message)),
      field("request_id", quote(request_id)),
      field("data", data_json),
      field("protocol_version", std::to_string(kProtocolVersion)),
  });
}

}  // namespace robot_core
