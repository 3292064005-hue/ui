cmake_minimum_required(VERSION 3.10)
project(SpineUltrasoundCore)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Force optimizations for Real-Time Core
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O3 -march=native -pthread")

# Include directories
include_directories(include)
include_directories(${CMAKE_CURRENT_BINARY_DIR})  # For generated protobuf files
# Assuming SDK is installed in `/usr/local` or `third_party/rokae/include`
# include_directories(${PROJECT_SOURCE_DIR}/../third_party/rokae/include)

# Find absolute dependencies for Zero-Copy and System Locking
find_package(Threads REQUIRED)
find_package(Protobuf REQUIRED)
find_package(OpenSSL REQUIRED)

# Protobuf generation
protobuf_generate_cpp(PROTO_SRCS PROTO_HDRS proto/ipc_messages.proto)

# Source files mapping
set(SOURCES
    src/main_ubuntu_rt.cpp
    src/rt_motion_service.cpp
    src/kinematics_validator.cpp
    ${PROTO_SRCS}
    # src/svd_calibration.cpp (If implemented entirely in C++)
)

# Build the Hard-RT Executable
add_executable(spine_robot_core ${SOURCES})

# Link libraries: POSIX threads, RealTime (-lrt), and hypothetically ROKAE's dynamic .so
target_link_libraries(spine_robot_core
    Threads::Threads
    protobuf::libprotobuf
    OpenSSL::SSL
    OpenSSL::Crypto
    rt
    # rokae_xcore_sdk 
)

# Install location matching the systemd service template
install(TARGETS spine_robot_core DESTINATION /opt/spine_ultrasound/cpp_robot_core/build)
