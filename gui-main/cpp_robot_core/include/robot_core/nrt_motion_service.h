#pragma once

#include <string>
#include <vector>

namespace robot_core {

class SdkRobotFacade;

struct NrtMotionSnapshot {
  bool ready{false};
  bool degraded_without_sdk{true};
  bool executor_wrapped{true};
  bool sdk_delegation_only{true};
  int command_count{0};
  std::string active_profile{"idle"};
  std::string last_command{""};
  std::string last_command_id{""};
  std::vector<std::string> blocking_profiles;
  std::vector<std::string> command_log;
};

class NrtMotionService {
public:
  explicit NrtMotionService(SdkRobotFacade* sdk = nullptr);

  void bind(SdkRobotFacade* sdk);
  bool goHome();
  bool approachPrescan();
  bool safeRetreat();
  NrtMotionSnapshot snapshot() const;

private:
  bool dispatchProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode);
  void record(const std::string& message);

  SdkRobotFacade* sdk_{nullptr};
  NrtMotionSnapshot snapshot_{};
};

}  // namespace robot_core
