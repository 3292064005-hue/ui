#pragma once
#include <functional>
#include <atomic>
#include <thread>
#include <chrono>
namespace robot_core {
class RecoveryManager {
public:
  RecoveryManager();
  ~RecoveryManager();

  void pauseAndHold();
  void controlledRetract();
  bool retreatCompleted() const;

  // Auto-retry functionality
  using RetryFunction = std::function<bool()>;
  void setRetryCallback(RetryFunction callback);
  void triggerRetry(int max_attempts = 3, std::chrono::milliseconds delay = std::chrono::milliseconds(1000));
  void cancelRetry();

private:
  void retryLoop();

  bool retreat_completed_{true};
  RetryFunction retry_callback_;
  std::atomic<bool> retry_active_{false};
  std::atomic<int> max_attempts_;
  std::chrono::milliseconds retry_delay_;
  std::thread retry_thread_;
};
}
