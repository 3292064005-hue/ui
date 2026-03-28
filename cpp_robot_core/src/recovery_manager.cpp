#include "robot_core/recovery_manager.h"
#include <iostream>
#include <thread>
#include <chrono>

namespace robot_core {

RecoveryManager::RecoveryManager() = default;

RecoveryManager::~RecoveryManager() {
  cancelRetry();
  if (retry_thread_.joinable()) {
    retry_thread_.join();
  }
}

void RecoveryManager::pauseAndHold() {
  retreat_completed_ = false;
}

void RecoveryManager::controlledRetract() {
  retreat_completed_ = true;
}

bool RecoveryManager::retreatCompleted() const {
  return retreat_completed_;
}

void RecoveryManager::setRetryCallback(RetryFunction callback) {
  retry_callback_ = std::move(callback);
}

void RecoveryManager::triggerRetry(int max_attempts, std::chrono::milliseconds delay) {
  if (retry_active_.load()) {
    return;  // Already retrying
  }

  max_attempts_ = max_attempts;
  retry_delay_ = delay;
  retry_active_.store(true);

  retry_thread_ = std::thread(&RecoveryManager::retryLoop, this);
}

void RecoveryManager::cancelRetry() {
  retry_active_.store(false);
}

void RecoveryManager::retryLoop() {
  for (int attempt = 1; attempt <= max_attempts_ && retry_active_.load(); ++attempt) {
    std::this_thread::sleep_for(retry_delay_);

    if (!retry_active_.load()) {
      break;
    }

    std::cout << "RecoveryManager: Retry attempt " << attempt << "/" << max_attempts_ << std::endl;

    if (retry_callback_ && retry_callback_()) {
      std::cout << "RecoveryManager: Retry succeeded on attempt " << attempt << std::endl;
      retry_active_.store(false);
      return;
    }
  }

  if (retry_active_.load()) {
    std::cout << "RecoveryManager: All retry attempts failed" << std::endl;
  }
  retry_active_.store(false);
}

}
