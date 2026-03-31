#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <memory>
#include <string>

#include "../../include/ipc_messages.hpp"
#include "../../include/impedance_control_manager.hpp"
#include "../../include/spsc_queue.hpp"

namespace rokae {
class xMateErProRobot;
}

namespace robot_core {

class SdkRobotFacade;

enum class SensorHealthDecision {
  None,
  Hold,
  ControlledRetract,
  Estop,
};

struct RtLoopContractSnapshot {
  bool loop_active{false};
  bool move_active{false};
  bool pause_hold{false};
  bool degraded_without_sdk{true};
  bool reference_limiter_enabled{true};
  bool freshness_guard_enabled{true};
  bool jitter_monitor_enabled{true};
  bool contact_band_monitor_enabled{true};
  int nominal_loop_hz{1000};
  std::string control_mode{"cartesianImpedance"};
  std::string phase{"idle"};
  std::string phase_group{"idle"};
  std::string last_event{"boot"};
  double desired_contact_force_n{0.0};
  double current_period_ms{1.0};
};

class AdaptiveTimer {
public:
  AdaptiveTimer(double min_period_ms = 0.5, double max_period_ms = 2.0, double target_cpu = 70.0);
  ~AdaptiveTimer() = default;

  void start();
  void wait();
  double getCurrentPeriodMs() const { return current_period_ms_; }
  void adjustPeriod(double cpu_usage);

private:
  double min_period_ms_;
  double max_period_ms_;
  double target_cpu_;
  double current_period_ms_;
  std::chrono::steady_clock::time_point last_time_;
  double getCpuUsage();
};

class RtMotionService {
public:
  explicit RtMotionService(std::shared_ptr<rokae::xMateErProRobot> robot = nullptr, SdkRobotFacade* sdk = nullptr);
  ~RtMotionService();

  spine_core::SPSCQueue<spine_core_pod::CommandPose> cmd_queue{100};
  spine_core::SPSCQueue<spine_core_pod::RobotTelemetry> telemetry_queue{100};

  void bindSdkFacade(SdkRobotFacade* sdk);
  bool startCartesianImpedance();
  void stop();
  void controlledRetract();
  SensorHealthDecision evaluateSensorFreshnessMs(double age_ms) const;
  bool seekContact();
  void pauseAndHold();
  RtLoopContractSnapshot snapshot() const;

private:
  void updateSnapshot(const std::string& phase, const std::string& event);

  std::shared_ptr<rokae::xMateErProRobot> robot_;
  SdkRobotFacade* sdk_{nullptr};
  std::unique_ptr<robot_core::ImpedanceControlManager> impedance_manager_;
  std::atomic<bool> is_running_{false};
  spine_core_pod::CommandPose current_target_{};
  std::unique_ptr<AdaptiveTimer> adaptive_timer_;
  RtLoopContractSnapshot snapshot_{};
};

}  // namespace robot_core
