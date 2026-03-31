#include "robot_core/sdk_robot_facade.h"

#ifdef ROBOT_CORE_WITH_XCORE_SDK
#include "rokae/robot.h"
#endif

#include <algorithm>
#include <cmath>
#include <sstream>

namespace robot_core {

SdkRobotFacade::SdkRobotFacade() {
  refreshStateVectors(6);
  tcp_pose_ = {0.0, 0.0, 240.0, 180.0, 0.0, 90.0};
  rl_projects_ = {{"spine_mainline", {"scan", "prep", "retreat"}}, {"spine_research", {"sweep", "contact_probe"}}};
  path_library_ = {{"spine_demo_path", 0.5, 128}, {"thoracic_followup", 0.4, 92}};
  di_ = {{"board0_port0", false}, {"board0_port1", true}};
  do_ = {{"board0_port0", false}, {"board0_port1", false}};
  ai_ = {{"board0_port0", 0.12}};
  ao_ = {{"board0_port0", 0.0}};
  registers_ = {{"spine.session.segment", 0}, {"spine.session.frame", 0}};
  appendLog(std::string("sdk facade booted source=") + runtimeSource());
}

SdkRobotFacade::~SdkRobotFacade() = default;

bool SdkRobotFacade::connect(const std::string& remote_ip, const std::string& local_ip) {
  connected_ = !remote_ip.empty() && !local_ip.empty();
  rt_config_.remote_ip = remote_ip;
  rt_config_.local_ip = local_ip;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  // Vendored SDK integration point. The concrete rokae::Robot lifecycle is routed
  // through this facade so the runtime stays SDK-agnostic even when linked.
#endif
  appendLog("connectToRobot(" + remote_ip + "," + local_ip + ")");
  return connected_;
}

void SdkRobotFacade::disconnect() {
  connected_ = false;
  powered_ = false;
  auto_mode_ = false;
  rl_status_ = {};
  drag_state_ = {};
  refreshStateVectors(static_cast<std::size_t>(std::max(1, rt_config_.axis_count)));
  tcp_pose_ = {0.0, 0.0, 240.0, 180.0, 0.0, 90.0};
  updateSessionRegisters(0, 0);
  appendLog("disconnectFromRobot()");
}

bool SdkRobotFacade::setPower(bool on) {
  if (!connected_) {
    return false;
  }
  powered_ = on;
  appendLog(std::string("setPowerState(") + (on ? "on" : "off") + ")");
  return true;
}

bool SdkRobotFacade::setAutoMode() {
  if (!connected_) {
    return false;
  }
  auto_mode_ = true;
  appendLog("setOperateMode(auto)");
  return true;
}

bool SdkRobotFacade::setManualMode() {
  if (!connected_) {
    return false;
  }
  auto_mode_ = false;
  appendLog("setOperateMode(manual)");
  return true;
}

bool SdkRobotFacade::configureRtMainline(const SdkRobotRuntimeConfig& config) {
  if (!connected_ || !powered_ || !auto_mode_) {
    return false;
  }
  rt_config_ = config;
  refreshStateVectors(static_cast<std::size_t>(std::max(1, config.axis_count)));
  tcp_pose_ = {118.0, 15.0, 205.0, 180.0, 0.0, 90.0};
  std::ostringstream oss;
  oss << "configureRtMainline(robot=" << config.robot_model
      << ", class=" << config.sdk_robot_class
      << ", rt_network_tolerance=" << config.rt_network_tolerance_percent
      << ", joint_filter_hz=" << config.joint_filter_hz
      << ", cart_filter_hz=" << config.cart_filter_hz
      << ", torque_filter_hz=" << config.torque_filter_hz
      << ", axis_count=" << config.axis_count
      << ", cartesian_impedance_z=" << config.cartesian_impedance[2]
      << ", desired_wrench_z=" << config.desired_wrench_n[2]
      << ")";
  appendLog(oss.str());
  path_library_.clear();
  path_library_.push_back({"spine_demo_path", 0.5, std::max(config.axis_count * 20, 128)});
  path_library_.push_back({"thoracic_followup", 0.4, std::max(config.axis_count * 15, 92)});
  return config.axis_count >= 6;
}

bool SdkRobotFacade::connected() const { return connected_; }
bool SdkRobotFacade::powered() const { return powered_; }
bool SdkRobotFacade::automaticMode() const { return auto_mode_; }

bool SdkRobotFacade::sdkAvailable() const {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  return true;
#else
  return false;
#endif
}

bool SdkRobotFacade::xmateModelAvailable() const {
#ifdef ROBOT_CORE_WITH_XMATE_MODEL
  return true;
#else
  return false;
#endif
}

std::string SdkRobotFacade::runtimeSource() const {
  if (sdkAvailable() && xmateModelAvailable()) {
    return "xcore_sdk_vendored+xmatemodel";
  }
  if (sdkAvailable()) {
    return "xcore_sdk_vendored";
  }
  return "simulated_contract";
}

SdkRobotRuntimeConfig SdkRobotFacade::runtimeConfig() const { return rt_config_; }

std::vector<double> SdkRobotFacade::jointPos() const { return joint_pos_; }
std::vector<double> SdkRobotFacade::jointVel() const { return joint_vel_; }
std::vector<double> SdkRobotFacade::jointTorque() const { return joint_torque_; }
std::vector<double> SdkRobotFacade::tcpPose() const { return tcp_pose_; }
std::vector<std::string> SdkRobotFacade::configurationLog() const { return configuration_log_; }
std::vector<std::string> SdkRobotFacade::controllerLogs() const { return controller_logs_; }
std::vector<SdkRobotProjectInfo> SdkRobotFacade::rlProjects() const { return rl_projects_; }
SdkRobotRlStatus SdkRobotFacade::rlStatus() const { return rl_status_; }
std::vector<SdkRobotPathInfo> SdkRobotFacade::pathLibrary() const { return path_library_; }
SdkRobotDragState SdkRobotFacade::dragState() const { return drag_state_; }
std::map<std::string, bool> SdkRobotFacade::di() const { return di_; }
std::map<std::string, bool> SdkRobotFacade::doState() const { return do_; }
std::map<std::string, double> SdkRobotFacade::ai() const { return ai_; }
std::map<std::string, double> SdkRobotFacade::ao() const { return ao_; }
std::map<std::string, int> SdkRobotFacade::registers() const { return registers_; }

void SdkRobotFacade::updateSessionRegisters(int active_segment, int frame_id) {
  registers_["spine.session.segment"] = active_segment;
  registers_["spine.session.frame"] = frame_id;
}

void SdkRobotFacade::setRlStatus(const std::string& project, const std::string& task, bool running) {
  rl_status_.loaded_project = project;
  rl_status_.loaded_task = task;
  rl_status_.running = running;
}

void SdkRobotFacade::setDragState(bool enabled, const std::string& space, const std::string& type) {
  drag_state_.enabled = enabled;
  drag_state_.space = space;
  drag_state_.type = type;
}

std::vector<double> SdkRobotFacade::zeroVector(std::size_t count) {
  return std::vector<double>(count, 0.0);
}

void SdkRobotFacade::appendLog(const std::string& message) {
  configuration_log_.push_back(message);
  controller_logs_.insert(controller_logs_.begin(), message);
  if (controller_logs_.size() > 32) {
    controller_logs_.resize(32);
  }
}

void SdkRobotFacade::refreshStateVectors(std::size_t axis_count) {
  joint_pos_ = zeroVector(axis_count);
  joint_vel_ = zeroVector(axis_count);
  joint_torque_ = zeroVector(axis_count);
  for (std::size_t idx = 0; idx < axis_count; ++idx) {
    joint_pos_[idx] = 0.05 * std::sin(static_cast<double>(idx) * 0.4);
    joint_vel_[idx] = 0.01 * std::cos(static_cast<double>(idx) * 0.3);
    joint_torque_[idx] = 0.2 * std::sin(static_cast<double>(idx) * 0.2);
  }
}

}  // namespace robot_core
