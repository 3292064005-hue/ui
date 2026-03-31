#include "robot_core/nrt_motion_service.h"

#include <sstream>

#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

NrtMotionService::NrtMotionService(SdkRobotFacade* sdk) : sdk_(sdk) {
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.blocking_profiles = {"go_home", "approach_prescan", "safe_retreat"};
}

void NrtMotionService::bind(SdkRobotFacade* sdk) {
  sdk_ = sdk;
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.executor_wrapped = true;
  snapshot_.sdk_delegation_only = true;
}

bool NrtMotionService::goHome() {
  return dispatchProfile("go_home", "MoveAbsJ", false);
}

bool NrtMotionService::approachPrescan() {
  return dispatchProfile("approach_prescan", "MoveL", true);
}

bool NrtMotionService::safeRetreat() {
  return dispatchProfile("safe_retreat", "MoveL", false);
}

NrtMotionSnapshot NrtMotionService::snapshot() const {
  return snapshot_;
}

bool NrtMotionService::dispatchProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode) {
  snapshot_.active_profile = profile;
  snapshot_.last_command = sdk_command;
  snapshot_.last_command_id = profile + "::" + std::to_string(snapshot_.command_count + 1);
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.ready = true;

  std::ostringstream oss;
  oss << "nrt profile=" << profile << " sdk_command=" << sdk_command
      << " policy=delegate_path_planning_to_sdk moveReset_before_batch=true";

  if (sdk_ != nullptr) {
    if (!sdk_->connected() || !sdk_->powered()) {
      record(oss.str() + " result=blocked reason=controller_not_ready");
      return false;
    }
    if (requires_auto_mode && !sdk_->automaticMode()) {
      record(oss.str() + " result=blocked reason=auto_mode_required");
      return false;
    }
    record(oss.str() + " result=accepted");
    return true;
  }

  record(oss.str() + " result=contract_only reason=no_sdk_binding");
  return true;
}

void NrtMotionService::record(const std::string& message) {
  snapshot_.command_count += 1;
  snapshot_.command_log.push_back(message);
  if (snapshot_.command_log.size() > 24) {
    snapshot_.command_log.erase(snapshot_.command_log.begin(), snapshot_.command_log.begin() + static_cast<long>(snapshot_.command_log.size() - 24));
  }
}

}  // namespace robot_core
