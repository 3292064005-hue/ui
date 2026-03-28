#include "robot_core/telemetry_publisher.h"

#include "json_utils.h"
#include <chrono>

namespace robot_core {

namespace {

constexpr int kProtocolVersion = 1;

int64_t nowNs() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             std::chrono::steady_clock::now().time_since_epoch())
      .count();
}

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
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

std::string envelope(const std::string& topic, const std::string& data_json) {
  using namespace json;
  return object({
      field("topic", quote(topic)),
      field("data", data_json),
      field("ts_ns", std::to_string(nowNs())),
      field("protocol_version", std::to_string(kProtocolVersion)),
  });
}

std::string deviceMapJson(const std::vector<DeviceHealth>& devices) {
  using namespace json;
  std::vector<std::string> fields;
  fields.reserve(devices.size());
  for (const auto& device : devices) {
    fields.push_back(
        field(
            device.device_name,
            object({
                field("connected", boolLiteral(device.online)),
                field("health", quote(device.online ? (device.fresh ? "online" : "stale") : "offline")),
                field("detail", quote(device.detail)),
                field("fresh", boolLiteral(device.fresh)),
                field("last_ts_ns", std::to_string(device.last_ts_ns)),
            })));
  }
  return object({field("devices", object(fields))});
}

}  // namespace

std::vector<std::string> TelemetryPublisher::buildLines(const TelemetrySnapshot& snapshot) const {
  using namespace json;
  std::vector<std::string> lines;
  lines.push_back(envelope(
      "core_state",
      object({
          field("execution_state", quote(stateName(snapshot.core_state.execution_state))),
          field("armed", boolLiteral(snapshot.core_state.armed)),
          field("fault_code", quote(snapshot.core_state.fault_code)),
          field("active_segment", std::to_string(snapshot.core_state.active_segment)),
          field("progress_pct", formatDouble(snapshot.core_state.progress_pct)),
          field("session_id", quote(snapshot.core_state.session_id)),
      })));
  lines.push_back(envelope(
      "robot_state",
      object({
          field("powered", boolLiteral(snapshot.robot_state.power_state == "on")),
          field("operate_mode", quote(snapshot.robot_state.operate_mode)),
          field("joint_pos", array(snapshot.robot_state.joint_pos)),
          field("joint_vel", array(snapshot.robot_state.joint_vel)),
          field("joint_torque", array(snapshot.robot_state.joint_torque)),
          field("cart_force", array(snapshot.robot_state.cart_force)),
          field(
              "tcp_pose",
              object({
                  field("x", snapshot.robot_state.tcp_pose.size() > 0 ? formatDouble(snapshot.robot_state.tcp_pose[0], 2) : "0.0"),
                  field("y", snapshot.robot_state.tcp_pose.size() > 1 ? formatDouble(snapshot.robot_state.tcp_pose[1], 2) : "0.0"),
                  field("z", snapshot.robot_state.tcp_pose.size() > 2 ? formatDouble(snapshot.robot_state.tcp_pose[2], 2) : "0.0"),
                  field("rx", snapshot.robot_state.tcp_pose.size() > 3 ? formatDouble(snapshot.robot_state.tcp_pose[3], 2) : "0.0"),
                  field("ry", snapshot.robot_state.tcp_pose.size() > 4 ? formatDouble(snapshot.robot_state.tcp_pose[4], 2) : "0.0"),
                  field("rz", snapshot.robot_state.tcp_pose.size() > 5 ? formatDouble(snapshot.robot_state.tcp_pose[5], 2) : "0.0"),
              })),
          field("last_event", quote(snapshot.robot_state.last_event)),
          field("last_controller_log", quote(snapshot.robot_state.last_controller_log)),
      })));
  lines.push_back(envelope(
      "contact_state",
      object({
          field("mode", quote(snapshot.contact_state.mode)),
          field("confidence", formatDouble(snapshot.contact_state.confidence)),
          field("pressure_current", formatDouble(snapshot.contact_state.pressure_current)),
          field("recommended_action", quote(snapshot.contact_state.recommended_action)),
      })));
  lines.push_back(envelope(
      "scan_progress",
      object({
          field("active_segment", std::to_string(snapshot.scan_progress.active_segment)),
          field("path_index", std::to_string(snapshot.scan_progress.path_index)),
          field("overall_progress", formatDouble(snapshot.scan_progress.overall_progress)),
          field("frame_id", std::to_string(snapshot.scan_progress.frame_id)),
      })));
  lines.push_back(envelope("device_health", deviceMapJson(snapshot.devices)));
  lines.push_back(envelope(
      "safety_status",
      object({
          field("safe_to_arm", boolLiteral(snapshot.safety_status.safe_to_arm)),
          field("safe_to_scan", boolLiteral(snapshot.safety_status.safe_to_scan)),
          field("active_interlocks", stringArray(snapshot.safety_status.active_interlocks)),
      })));
  lines.push_back(envelope(
      "recording_status",
      object({
          field("session_id", quote(snapshot.recorder_status.session_id)),
          field("recording", boolLiteral(snapshot.recorder_status.recording)),
          field("dropped_samples", std::to_string(snapshot.recorder_status.dropped_samples)),
          field("last_flush_ns", std::to_string(snapshot.recorder_status.last_flush_ns)),
      })));
  lines.push_back(envelope(
      "quality_feedback",
      object({
          field("image_quality", formatDouble(snapshot.quality_feedback.image_quality)),
          field("feature_confidence", formatDouble(snapshot.quality_feedback.feature_confidence)),
          field("quality_score", formatDouble(snapshot.quality_feedback.quality_score)),
          field("need_resample", boolLiteral(snapshot.quality_feedback.need_resample)),
      })));
  for (const auto& alarm : snapshot.alarms) {
    lines.push_back(envelope(
        "alarm_event",
        object({
            field("severity", quote(alarm.severity)),
            field("source", quote(alarm.source)),
            field("message", quote(alarm.message)),
            field("session_id", quote(alarm.session_id)),
            field("segment_id", std::to_string(alarm.segment_id)),
            field("event_ts_ns", std::to_string(alarm.event_ts_ns)),
        })));
  }
  return lines;
}

std::vector<spine_core::RobotTelemetry> TelemetryPublisher::buildProtobufMessages(const TelemetrySnapshot& snapshot) const {
  std::vector<spine_core::RobotTelemetry> messages;
  int64_t ts = nowNs();

  // Core state
  {
    spine_core::RobotTelemetry msg;
    msg.set_protocol_version(kProtocolVersion);
    msg.set_topic("core_state");
    msg.set_ts_ns(ts);
    msg.add_tcp_pose_measured(static_cast<double>(snapshot.core_state.execution_state));  // Simplified
    msg.set_safety_status(snapshot.core_state.armed ? 1 : 0);
    messages.push_back(msg);
  }

  // Robot state
  {
    spine_core::RobotTelemetry msg;
    msg.set_protocol_version(kProtocolVersion);
    msg.set_topic("robot_state");
    msg.set_ts_ns(ts);
    for (double pos : snapshot.robot_state.joint_pos) {
      msg.add_joint_pos(pos);
    }
    for (double torque : snapshot.robot_state.joint_torque) {
      msg.add_joint_torque(torque);
    }
    for (double pose : snapshot.robot_state.tcp_pose) {
      msg.add_tcp_pose_measured(pose);
    }
    msg.set_actual_force_z(snapshot.robot_state.cart_force.empty() ? 0.0 : snapshot.robot_state.cart_force[2]);
    msg.set_safety_status(snapshot.robot_state.power_state == "on" ? 1 : 0);
    messages.push_back(msg);
  }

  // Add other topics similarly...
  // For brevity, only core and robot state are implemented

  return messages;
}

}  // namespace robot_core
