#pragma once

#include <array>
#include <cstddef>
#include <map>
#include <string>
#include <vector>

namespace robot_core {

struct SdkRobotRuntimeConfig {
  std::string robot_model{"xmate3"};
  std::string sdk_robot_class{"xMateRobot"};
  std::string preferred_link{"wired_direct"};
  bool requires_single_control_source{true};
  std::string clinical_mainline_mode{"cartesianImpedance"};
  std::string remote_ip{"192.168.0.160"};
  std::string local_ip{"192.168.0.100"};
  int axis_count{6};
  int rt_network_tolerance_percent{15};
  double joint_filter_hz{40.0};
  double cart_filter_hz{30.0};
  double torque_filter_hz{25.0};
  std::array<double, 6> cartesian_impedance{{1000.0, 1000.0, 1000.0, 80.0, 80.0, 80.0}};
  std::array<double, 6> desired_wrench_n{{0.0, 0.0, 8.0, 0.0, 0.0, 0.0}};
  std::array<double, 16> fc_frame_matrix{{1.0, 0.0, 0.0, 0.0,
                                          0.0, 1.0, 0.0, 0.0,
                                          0.0, 0.0, 1.0, 0.0,
                                          0.0, 0.0, 0.0, 1.0}};
  std::array<double, 16> tcp_frame_matrix{{1.0, 0.0, 0.0, 0.0,
                                           0.0, 1.0, 0.0, 0.0,
                                           0.0, 0.0, 1.0, 62.0,
                                           0.0, 0.0, 0.0, 1.0}};
  std::array<double, 3> load_com_mm{{0.0, 0.0, 62.0}};
  std::array<double, 6> load_inertia{{0.0012, 0.0012, 0.0008, 0.0, 0.0, 0.0}};
};

struct SdkRobotProjectInfo {
  std::string name;
  std::vector<std::string> tasks;
};

struct SdkRobotPathInfo {
  std::string name;
  double rate{0.0};
  int points{0};
};

struct SdkRobotRlStatus {
  std::string loaded_project;
  std::string loaded_task;
  bool running{false};
  double rate{1.0};
  bool loop{false};
};

struct SdkRobotDragState {
  bool enabled{false};
  std::string space{"cartesian"};
  std::string type{"admittance"};
};

class SdkRobotFacade {
public:
  SdkRobotFacade();
  ~SdkRobotFacade();

  bool connect(const std::string& remote_ip, const std::string& local_ip);
  void disconnect();
  bool setPower(bool on);
  bool setAutoMode();
  bool setManualMode();
  bool configureRtMainline(const SdkRobotRuntimeConfig& config);
  bool connected() const;
  bool powered() const;
  bool automaticMode() const;
  bool sdkAvailable() const;
  bool xmateModelAvailable() const;
  std::string runtimeSource() const;
  SdkRobotRuntimeConfig runtimeConfig() const;
  std::vector<double> jointPos() const;
  std::vector<double> jointVel() const;
  std::vector<double> jointTorque() const;
  std::vector<double> tcpPose() const;
  std::vector<std::string> configurationLog() const;
  std::vector<std::string> controllerLogs() const;
  std::vector<SdkRobotProjectInfo> rlProjects() const;
  SdkRobotRlStatus rlStatus() const;
  std::vector<SdkRobotPathInfo> pathLibrary() const;
  SdkRobotDragState dragState() const;
  std::map<std::string, bool> di() const;
  std::map<std::string, bool> doState() const;
  std::map<std::string, double> ai() const;
  std::map<std::string, double> ao() const;
  std::map<std::string, int> registers() const;
  void updateSessionRegisters(int active_segment, int frame_id);
  void setRlStatus(const std::string& project, const std::string& task, bool running);
  void setDragState(bool enabled, const std::string& space, const std::string& type);

private:
  static std::vector<double> zeroVector(std::size_t count);
  void appendLog(const std::string& message);
  void refreshStateVectors(std::size_t axis_count);

  bool connected_{false};
  bool powered_{false};
  bool auto_mode_{false};
  SdkRobotRuntimeConfig rt_config_{};
  std::vector<double> joint_pos_;
  std::vector<double> joint_vel_;
  std::vector<double> joint_torque_;
  std::vector<double> tcp_pose_;
  std::vector<std::string> configuration_log_;
  std::vector<std::string> controller_logs_;
  std::vector<SdkRobotProjectInfo> rl_projects_;
  SdkRobotRlStatus rl_status_{};
  std::vector<SdkRobotPathInfo> path_library_;
  SdkRobotDragState drag_state_{};
  std::map<std::string, bool> di_;
  std::map<std::string, bool> do_;
  std::map<std::string, double> ai_;
  std::map<std::string, double> ao_;
  std::map<std::string, int> registers_;
};

}  // namespace robot_core
