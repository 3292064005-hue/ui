#include "robot_core/command_server.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstring>
#include <iostream>
#include <openssl/ssl.h>
#include <openssl/err.h>

#include "ipc_messages.pb.h"  // Generated protobuf header

namespace robot_core {

namespace {

int openServerSocket(int port) {
  int fd = ::socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    return -1;
  }
  int reuse = 1;
  ::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_ANY);
  addr.sin_port = htons(static_cast<uint16_t>(port));
  if (::bind(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
    ::close(fd);
    return -1;
  }
  if (::listen(fd, 16) != 0) {
    ::close(fd);
    return -1;
  }
  return fd;
}

SSL_CTX* createTLSContext() {
  const SSL_METHOD* method = TLS_server_method();
  SSL_CTX* ctx = SSL_CTX_new(method);
  if (!ctx) {
    std::cerr << "Unable to create SSL context" << std::endl;
    return nullptr;
  }

  // Set TLS 1.3 only
  SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
  SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);

  // Load certificate and private key (self-signed for demo)
  if (SSL_CTX_use_certificate_file(ctx, "server.crt", SSL_FILETYPE_PEM) <= 0) {
    std::cerr << "Failed to load certificate" << std::endl;
    SSL_CTX_free(ctx);
    return nullptr;
  }

  if (SSL_CTX_use_PrivateKey_file(ctx, "server.key", SSL_FILETYPE_PEM) <= 0) {
    std::cerr << "Failed to load private key" << std::endl;
    SSL_CTX_free(ctx);
    return nullptr;
  }

  return ctx;
}

bool sendProtobufSSL(SSL* ssl, const google::protobuf::Message& msg) {
  std::string serialized;
  if (!msg.SerializeToString(&serialized)) {
    return false;
  }
  // Send length prefix (4 bytes, big-endian)
  uint32_t length = htonl(serialized.size());
  if (SSL_write(ssl, &length, sizeof(length)) != sizeof(length)) {
    return false;
  }
  // Send message
  int sent = 0;
  while (sent < static_cast<int>(serialized.size())) {
    int rc = SSL_write(ssl, serialized.data() + sent, serialized.size() - sent);
    if (rc <= 0) {
      return false;
    }
    sent += rc;
  }
  return true;
}

bool receiveProtobufSSL(SSL* ssl, google::protobuf::Message& msg) {
  // Receive length prefix
  uint32_t length;
  if (SSL_read(ssl, &length, sizeof(length)) != sizeof(length)) {
    return false;
  }
  length = ntohl(length);
  // Receive message
  std::string serialized(length, '\0');
  int received = 0;
  while (received < static_cast<int>(length)) {
    int rc = SSL_read(ssl, &serialized[received], length - received);
    if (rc <= 0) {
      return false;
    }
    received += rc;
  }
  return msg.ParseFromString(serialized);
}

std::string CommandServer::handleCommandProtobuf(const spine_core::Command& cmd) {
  // Convert protobuf command to JSON-like string for runtime
  std::string json_cmd = "{";
  json_cmd += "\"protocol_version\":" + std::to_string(cmd.protocol_version()) + ",";
  json_cmd += "\"command\":\"" + cmd.command() + "\",";
  json_cmd += "\"payload\":\"" + cmd.payload() + "\",";
  json_cmd += "\"request_id\":" + std::to_string(cmd.request_id());
  json_cmd += "}";
  return runtime_.handleCommandJson(json_cmd);
}

}  // namespace

CommandServer::CommandServer(int command_port, int telemetry_port)
    : command_port_(command_port), telemetry_port_(telemetry_port) {
  // Initialize OpenSSL
  SSL_library_init();
  OpenSSL_add_all_algorithms();
  SSL_load_error_strings();

  ssl_ctx_ = createTLSContext();
  if (!ssl_ctx_) {
    std::cerr << "Failed to create TLS context" << std::endl;
  }
}

CommandServer::~CommandServer() {
  stop();
  if (ssl_ctx_) {
    SSL_CTX_free(ssl_ctx_);
  }
}

void CommandServer::setState(RobotCoreState state) {
  state_ = state;
  runtime_.setState(state);
}

RobotCoreState CommandServer::state() const {
  return runtime_.state();
}

void CommandServer::spin() {
  command_server_fd_ = openServerSocket(command_port_);
  telemetry_server_fd_ = openServerSocket(telemetry_port_);
  if (command_server_fd_ < 0 || telemetry_server_fd_ < 0) {
    std::cerr << "failed to open robot_core sockets" << std::endl;
    stop();
    return;
  }
  std::cout << "robot_core command server on 0.0.0.0:" << command_port_ << std::endl;
  std::cout << "robot_core telemetry server on 0.0.0.0:" << telemetry_port_ << std::endl;

  command_thread_ = std::thread(&CommandServer::commandAcceptLoop, this);
  telemetry_accept_thread_ = std::thread(&CommandServer::telemetryAcceptLoop, this);
  rt_thread_ = std::thread(&CommandServer::rtLoop, this);
  state_poll_thread_ = std::thread(&CommandServer::statePollLoop, this);
  watchdog_thread_ = std::thread(&CommandServer::watchdogLoop, this);
  telemetry_thread_ = std::thread(&CommandServer::telemetryLoop, this);

  command_thread_.join();
  telemetry_accept_thread_.join();
  rt_thread_.join();
  state_poll_thread_.join();
  watchdog_thread_.join();
  telemetry_thread_.join();
}

void CommandServer::stop() {
  stop_requested_.store(true);
  if (command_server_fd_ >= 0) {
    ::shutdown(command_server_fd_, SHUT_RDWR);
    ::close(command_server_fd_);
    command_server_fd_ = -1;
  }
  if (telemetry_server_fd_ >= 0) {
    ::shutdown(telemetry_server_fd_, SHUT_RDWR);
    ::close(telemetry_server_fd_);
    telemetry_server_fd_ = -1;
  }
  {
    std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
    for (int fd : telemetry_clients_) {
      ::shutdown(fd, SHUT_RDWR);
      ::close(fd);
    }
    telemetry_clients_.clear();
  }
}

void CommandServer::commandAcceptLoop() {
  while (!stop_requested_.load()) {
    const int client_fd = ::accept(command_server_fd_, nullptr, nullptr);
    if (client_fd < 0) {
      if (stop_requested_.load()) {
        return;
      }
      continue;
    }

    // Establish TLS connection
    SSL* ssl = SSL_new(ssl_ctx_);
    if (!ssl) {
      std::cerr << "Failed to create SSL object" << std::endl;
      ::shutdown(client_fd, SHUT_RDWR);
      ::close(client_fd);
      continue;
    }

    SSL_set_fd(ssl, client_fd);
    if (SSL_accept(ssl) <= 0) {
      std::cerr << "TLS handshake failed" << std::endl;
      SSL_free(ssl);
      ::shutdown(client_fd, SHUT_RDWR);
      ::close(client_fd);
      continue;
    }

    spine_core::Command cmd;
    if (!receiveProtobufSSL(ssl, cmd)) {
      SSL_free(ssl);
      ::shutdown(client_fd, SHUT_RDWR);
      ::close(client_fd);
      continue;
    }
    const auto reply_json = handleCommandProtobuf(cmd);
    // Convert reply JSON to protobuf response (simplified)
    spine_core::Command reply;
    reply.set_protocol_version(1);
    reply.set_command("response");
    reply.set_payload(reply_json);
    reply.set_request_id(cmd.request_id());
    sendProtobufSSL(ssl, reply);
    SSL_free(ssl);
    ::shutdown(client_fd, SHUT_RDWR);
    ::close(client_fd);
    const auto lines = telemetry_publisher_.buildLines(runtime_.takeTelemetrySnapshot());
    std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
    broadcastLocked(lines);
  }
}

void CommandServer::telemetryAcceptLoop() {
  while (!stop_requested_.load()) {
    const int client_fd = ::accept(telemetry_server_fd_, nullptr, nullptr);
    if (client_fd < 0) {
      if (stop_requested_.load()) {
        return;
      }
      continue;
    }
    {
      std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
      telemetry_clients_.push_back(client_fd);
      broadcastLocked(telemetry_publisher_.buildLines(runtime_.takeTelemetrySnapshot()));
    }
  }
}

void CommandServer::rtLoop() {
  while (!stop_requested_.load()) {
    runtime_.rtStep();
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
}

void CommandServer::statePollLoop() {
  while (!stop_requested_.load()) {
    runtime_.statePollStep();
    std::this_thread::sleep_for(std::chrono::milliseconds(4));
  }
}

void CommandServer::watchdogLoop() {
  while (!stop_requested_.load()) {
    runtime_.watchdogStep();
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
}

void CommandServer::telemetryLoop() {
  while (!stop_requested_.load()) {
    const auto messages = telemetry_publisher_.buildProtobufMessages(runtime_.takeTelemetrySnapshot());
    {
      std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
      broadcastProtobufLocked(messages);
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
  }
}

void CommandServer::broadcastProtobufLocked(const std::vector<spine_core::RobotTelemetry>& messages) {
  std::vector<int> alive;
  alive.reserve(telemetry_clients_.size());
  for (int fd : telemetry_clients_) {
    bool ok = true;
    for (const auto& msg : messages) {
      if (!sendProtobuf(fd, msg)) {
        ok = false;
        break;
      }
    }
    if (ok) {
      alive.push_back(fd);
    } else {
      ::shutdown(fd, SHUT_RDWR);
      ::close(fd);
    }
  }
  telemetry_clients_ = std::move(alive);
}
  }
  telemetry_clients_.swap(alive);
}

}  // namespace robot_core
