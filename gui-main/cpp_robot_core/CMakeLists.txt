cmake_minimum_required(VERSION 3.10)
project(SpineUltrasoundCore)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MODULE_PATH ${CMAKE_MODULE_PATH} "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

option(ROBOT_CORE_WITH_XCORE_SDK "Enable direct xCore SDK integration hooks" ON)
option(ROBOT_CORE_WITH_XMATE_MODEL "Enable xMateModel support when vendored SDK is available" ON)
set(XCORE_SDK_ROOT "" CACHE PATH "Path to xCore SDK root")
if(NOT XCORE_SDK_ROOT AND DEFINED ENV{XCORE_SDK_ROOT})
  set(XCORE_SDK_ROOT "$ENV{XCORE_SDK_ROOT}" CACHE PATH "Path to xCore SDK root" FORCE)
endif()
if(NOT XCORE_SDK_ROOT AND DEFINED ENV{ROKAE_SDK_ROOT})
  set(XCORE_SDK_ROOT "$ENV{ROKAE_SDK_ROOT}" CACHE PATH "Path to xCore SDK root" FORCE)
endif()
if(NOT XCORE_SDK_ROOT)
  set(_VENDORED_SDK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../third_party/rokae_xcore_sdk/robot")
  if(EXISTS "${_VENDORED_SDK_ROOT}/include/rokae/robot.h")
    set(XCORE_SDK_ROOT "${_VENDORED_SDK_ROOT}" CACHE PATH "Path to xCore SDK root" FORCE)
  endif()
endif()

# Force optimizations for Real-Time Core
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -pthread")

find_package(Threads REQUIRED)
find_package(Protobuf REQUIRED)
find_package(OpenSSL REQUIRED)
find_package(Eigen3 REQUIRED)
enable_testing()

if(ROBOT_CORE_WITH_XCORE_SDK)
  find_package(VendoredRokaeSdk QUIET)
  if(VendoredRokaeSdk_FOUND)
    add_compile_definitions(ROBOT_CORE_WITH_XCORE_SDK=1)
    if(ROBOT_CORE_WITH_XMATE_MODEL AND TARGET Rokae::xMateModel)
      add_compile_definitions(ROBOT_CORE_WITH_XMATE_MODEL=1)
    endif()
  else()
    message(WARNING "ROBOT_CORE_WITH_XCORE_SDK=ON but vendored SDK was not found. Falling back to simulated contract runtime.")
  endif()
endif()

add_compile_definitions(
  ROBOT_CORE_FORCE_CONTROL_CONFIG_PATH="${CMAKE_SOURCE_DIR}/../configs/force_control.json"
  ROBOT_CORE_DEFAULT_ROBOT_MODEL="xmate3"
  ROBOT_CORE_DEFAULT_SDK_CLASS="xMateRobot"
)

include_directories(include)
include_directories(${CMAKE_CURRENT_BINARY_DIR})
include_directories(/usr/include/eigen3)
if(VendoredRokaeSdk_FOUND)
  include_directories(${VendoredRokaeSdk_INCLUDE_DIR})
  include_directories(${VendoredRokaeSdk_EXTERNAL_DIR})
endif()

protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS proto/ipc_messages.proto)

set(CORE_RUNTIME_SOURCES
    src/command_server.cpp
    src/core_runtime.cpp
    src/contact_gate.cpp
    src/contact_observer.cpp
    src/nrt_motion_service.cpp
    src/recording_service.cpp
    src/protobuf_protocol.cpp
    src/recovery_manager.cpp
    src/recovery_policy.cpp
    src/robot_state_hub.cpp
    src/scan_plan_parser.cpp
    src/scan_plan_validator.cpp
    src/state_machine_guard.cpp
    src/rt_motion_service.cpp
    src/safety_service.cpp
    src/sdk_robot_facade.cpp
    src/telemetry_publisher.cpp
    src/trajectory_compiler.cpp
    src/kinematics_validator.cpp
    src/pose_interpolator.cpp
    ${PROTO_SRCS}
)

add_library(spine_robot_core_runtime STATIC ${CORE_RUNTIME_SOURCES})
add_executable(spine_robot_core src/main_ubuntu_rt.cpp)
add_executable(test_seqlock src/test_seqlock.cpp)
add_executable(test_force_control src/test_force_control.cpp)
add_executable(test_impedance_scan src/test_impedance_scan.cpp)
add_executable(test_protocol_bridge src/test_protocol_bridge.cpp)
add_executable(test_recovery_manager src/test_recovery_manager.cpp)
add_executable(impedance_scan_example src/impedance_scan_example.cpp)

target_link_libraries(spine_robot_core_runtime
    Threads::Threads
    protobuf::libprotobuf
    OpenSSL::SSL
    OpenSSL::Crypto
    rt
)

if(VendoredRokaeSdk_FOUND)
  target_link_libraries(spine_robot_core_runtime PRIVATE Rokae::xCoreSDK)
endif()

target_link_libraries(spine_robot_core spine_robot_core_runtime)

target_link_libraries(test_seqlock
    Threads::Threads
    rt
)

target_link_libraries(test_force_control
    spine_robot_core_runtime
    Threads::Threads
)

target_link_libraries(test_impedance_scan
    Threads::Threads
)

target_link_libraries(test_protocol_bridge
    spine_robot_core_runtime
)

target_link_libraries(test_recovery_manager
    spine_robot_core_runtime
)

target_link_libraries(impedance_scan_example
    Threads::Threads
)

add_test(NAME cpp_force_control COMMAND test_force_control)
add_test(NAME cpp_impedance_scan COMMAND test_impedance_scan)
add_test(NAME cpp_protocol_bridge COMMAND test_protocol_bridge)
add_test(NAME cpp_recovery_manager COMMAND test_recovery_manager)

install(TARGETS spine_robot_core DESTINATION /opt/spine_ultrasound/cpp_robot_core/build)
