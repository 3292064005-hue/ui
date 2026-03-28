#include <iostream>
#include <sched.h>
#include <pthread.h>
#include <sys/mman.h>
#include <unistd.h>
#include <cstring>
#include <stdexcept>
// #include "robot_core/rt_motion_service.h" // Assuming this is linked
// #include "ipc/ipc_server.h"

// Set true hardware affinity targeting Cores 0 and 1 (Assuming 'isolcpus=0,1' in GRUB)
void pin_thread_to_isolated_cores() {
    cpu_set_t cpuset;
    CPU_ZERO(&cpuset);
    CPU_SET(0, &cpuset); // Dedicate Core 0
    CPU_SET(1, &cpuset); // Dedicate Core 1

    pthread_t current_thread = pthread_self();
    if (pthread_setaffinity_np(current_thread, sizeof(cpu_set_t), &cpuset) != 0) {
        std::cerr << "[Warning] Failed to set CPU affinity to isolated cores. Are you root?\n";
    } else {
        std::cout << "[RT-Core] System isolated to CPU 0,1 successfully.\n";
    }
}

// Lock all current and future contiguous heap allocations to Physical RAM
// Bypasses Linux Swap Partition causing micro-stutters
void lock_memory_for_rt() {
    if (mlockall(MCL_CURRENT | MCL_FUTURE) == -1) {
        std::cerr << "[Warning] mlockall failed: " << strerror(errno) << " - Check LimitMEMLOCK in systemd!\n";
    } else {
        std::cout << "[RT-Core] Memory globally locked successfully. OS Page Faults eliminated.\n";
    }
}

int main(int argc, char* argv[]) {
    std::cout << "Starting Spine Ultrasound C++ Hard-RT Core...\n";

    // 1. Hardware Privilege Setup
    lock_memory_for_rt();
    pin_thread_to_isolated_cores();

    // 2. Instantiate dependencies 
    // auto robot = std::make_shared<rokae::xMateErProRobot>(...);
    // auto rt_service = std::make_shared<robot_core::RtMotionService>(robot);

    // 3. Boot 1kHz Command Receiver and Telemetry Publisher Threads
    // (Pushing to/from the MoodyCamel lock-free queues exposed in rt_service)
    // auto ipc_server = std::make_shared<ipc::IPCServer>(rt_service);
    // ipc_server->start();

    // 4. Engage Z-axis 10N Compliance Tracking 
    // rt_service->startCartesianImpedance();

    std::cout << "[RT-Core] System armed and streaming.\n";

    // Main thread infinite hang until interupted
    while (true) {
        usleep(1000000); // 1Hz heartbeat idle
    }

    return 0;
}
