#include <iostream>
#include "robot_core/command_server.h"

int main() {
  std::cout << "robot_core runtime started" << std::endl;
  robot_core::CommandServer server;
  server.spin();
  return 0;
}
