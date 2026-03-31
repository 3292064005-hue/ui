#include "robot_core/rt_motion_service.h"

#include <array>
#include <cstring>
#include <fstream>
#include <sstream>
#include <thread>

#include "robot_core/sdk_robot_facade.h"

namespace rokae {
struct CartesianPosition { std::array<double, 16> pos; };
enum CoordinateType { endInRef };
enum FrameType { path };
enum RtControllerMode { cartesianImpedance };
enum RtSupportedFields { tcpPose_m, tau_m };
}  // namespace rokae

namespace robot_core {

AdaptiveTimer::AdaptiveTimer(double min_period_ms, double max_period_ms, double target_cpu)
    : min_period_ms_(min_period_ms),
      max_period_ms_(max_period_ms),
      target_cpu_(target_cpu),
      current_period_ms_(1.0) {}

void AdaptiveTimer::start() {
  last_time_ = std::chrono::steady_clock::now();
}

void AdaptiveTimer::wait() {
  const auto now = std::chrono::steady_clock::now();
  const auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(now - last_time_).count();
  const double elapsed_ms = static_cast<double>(elapsed) / 1000.0;
  if (elapsed_ms < current_period_ms_) {
    std::this_thread::sleep_for(std::chrono::microseconds(static_cast<long>((current_period_ms_ - elapsed_ms) * 1000.0)));
  }
  last_time_ = std::chrono::steady_clock::now();
}

void AdaptiveTimer::adjustPeriod(double cpu_usage) {
  if (cpu_usage > target_cpu_ + 10.0) {
    current_period_ms_ = std::min(current_period_ms_ * 1.1, max_period_ms_);
  } else if (cpu_usage < target_cpu_ - 10.0) {
    current_period_ms_ = std::max(current_period_ms_ * 0.9, min_period_ms_);
  }
}

double AdaptiveTimer::getCpuUsage() {
  std::ifstream file("/proc/stat");
  std::string line;
  if (std::getline(file, line)) {
    std::istringstream iss(line);
    std::string cpu;
    long user = 0;
    long nice = 0;
    long system = 0;
    long idle = 0;
    long iowait = 0;
    long irq = 0;
    long softirq = 0;
    iss >> cpu >> user >> nice >> system >> idle >> iowait >> irq >> softirq;
    const long total = user + nice + system + idle + iowait + irq + softirq;
    static long prev_total = 0;
    static long prev_idle = 0;
    const long total_diff = total - prev_total;
    const long idle_diff = idle - prev_idle;
    prev_total = total;
    prev_idle = idle;
    if (total_diff > 0) {
      return 100.0 * (1.0 - static_cast<double>(idle_diff) / static_cast<double>(total_diff));
    }
  }
  return 0.0;
}

inline int64_t get_current_time_ns() {
  const auto now = std::chrono::steady_clock::now();
  return std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count();
}

RtMotionService::RtMotionService(std::shared_ptr<rokae::xMateErProRobot> robot, SdkRobotFacade* sdk)
    : robot_(std::move(robot)),
      sdk_(sdk),
      cmd_queue(100),
      telemetry_queue(100),
      adaptive_timer_(std::make_unique<AdaptiveTimer>()),
      impedance_manager_(std::make_unique<ImpedanceControlManager>()) {
  std::memset(current_target_.tcp_pose_td, 0, sizeof(current_target_.tcp_pose_td));
  current_target_.tcp_pose_td[0] = 1.0;
  current_target_.tcp_pose_td[5] = 1.0;
  current_target_.tcp_pose_td[10] = 1.0;
  current_target_.tcp_pose_td[15] = 1.0;
  current_target_.timestamp_ns = get_current_time_ns();
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.desired_contact_force_n = impedance_manager_->getCircuitBreaker().getLimits().desired_contact_force_n;
  snapshot_.reference_limiter_enabled = true;
  snapshot_.freshness_guard_enabled = true;
  snapshot_.jitter_monitor_enabled = true;
  snapshot_.contact_band_monitor_enabled = true;
  snapshot_.nominal_loop_hz = 1000;
}

RtMotionService::~RtMotionService() {
  stop();
}

void RtMotionService::bindSdkFacade(SdkRobotFacade* sdk) {
  sdk_ = sdk;
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
}

bool RtMotionService::startCartesianImpedance() {
  if (sdk_ != nullptr && (!sdk_->connected() || !sdk_->powered() || !sdk_->automaticMode() || !sdk_->rtMainlineConfigured())) {
    updateSnapshot("blocked", "rt_preconditions_missing");
    return false;
  }

  is_running_ = true;
  adaptive_timer_->start();

  CartesianImpedanceParams params;
  params.stiffness = {1500.0, 1500.0, 20.0, 100.0, 100.0, 100.0};
  params.damping = {50.0, 50.0, 10.0, 20.0, 20.0, 20.0};
  if (!impedance_manager_->configureImpedance(params)) {
    is_running_ = false;
    updateSnapshot("fault", "impedance_config_failed");
    return false;
  }

  const auto& force_limits = impedance_manager_->getCircuitBreaker().getLimits();
  impedance_manager_->setDesiredWrench({0.0, 0.0, -std::abs(force_limits.desired_contact_force_n), 0.0, 0.0, 0.0});
  impedance_manager_->activateImpedance();
  snapshot_.desired_contact_force_n = force_limits.desired_contact_force_n;
  updateSnapshot("scan_follow", "start_cartesian_impedance");
  return true;
}

void RtMotionService::controlledRetract() {
  is_running_ = false;
  impedance_manager_->setDesiredWrench({0.0, 0.0, 0.0, 0.0, 0.0, 0.0});
  impedance_manager_->deactivateImpedance();
  snapshot_.pause_hold = false;
  updateSnapshot("controlled_retract", "controlled_retract");
}

SensorHealthDecision RtMotionService::evaluateSensorFreshnessMs(double age_ms) const {
  const auto& limits = impedance_manager_->getCircuitBreaker().getLimits();
  if (age_ms > limits.sensor_timeout_ms * 2.0) {
    return SensorHealthDecision::Estop;
  }
  if (age_ms > limits.sensor_timeout_ms) {
    return SensorHealthDecision::ControlledRetract;
  }
  if (age_ms > limits.stale_telemetry_ms) {
    return SensorHealthDecision::Hold;
  }
  return SensorHealthDecision::None;
}

void RtMotionService::stop() {
  is_running_ = false;
  impedance_manager_->deactivateImpedance();
  snapshot_.pause_hold = false;
  updateSnapshot("idle", "stop");
}

bool RtMotionService::seekContact() {
  if (sdk_ != nullptr && (!sdk_->connected() || !sdk_->powered())) {
    updateSnapshot("blocked", "seek_contact_preconditions_missing");
    return false;
  }
  impedance_manager_->setDesiredContactForce(impedance_manager_->getCircuitBreaker().getLimits().desired_contact_force_n);
  impedance_manager_->activateImpedance();
  updateSnapshot("seek_contact", "seek_contact");
  return true;
}

void RtMotionService::pauseAndHold() {
  impedance_manager_->setDesiredContactForce(0.0);
  impedance_manager_->activateImpedance();
  snapshot_.pause_hold = true;
  updateSnapshot("pause_hold", "pause_and_hold");
}

RtLoopContractSnapshot RtMotionService::snapshot() const {
  return snapshot_;
}

void RtMotionService::updateSnapshot(const std::string& phase, const std::string& event) {
  snapshot_.loop_active = is_running_.load();
  snapshot_.move_active = is_running_.load();
  snapshot_.phase = phase;
  snapshot_.phase_group = (phase == "seek_contact" ? "contact" : (phase == "contact_hold" || phase == "scan_follow" || phase == "pause_hold" ? "scan" : (phase == "controlled_retract" ? "recovery" : "idle")));
  snapshot_.last_event = event;
  snapshot_.control_mode = "cartesianImpedance";
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.current_period_ms = adaptive_timer_->getCurrentPeriodMs();
}

}  // namespace robot_core
