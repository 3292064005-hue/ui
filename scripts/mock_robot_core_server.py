#!/usr/bin/env python3
from __future__ import annotations

import json
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.ipc_protocol import CommandEnvelope
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime

HOST = "127.0.0.1"
COMMAND_PORT = 5656
TELEMETRY_PORT = 5657

runtime = MockCoreRuntime()
telemetry_clients = []
lock = threading.Lock()


def jsend(sock, obj):
    sock.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))


def handle_command(conn):
    with conn:
        file = conn.makefile("r", encoding="utf-8")
        for line in file:
            line = line.strip()
            if not line:
                continue
            req = CommandEnvelope.from_json(line)
            with lock:
                reply = runtime.handle_command(req.command, req.payload)
                reply.request_id = req.request_id
                snapshot = runtime.telemetry_snapshot()
            jsend(conn, json.loads(reply.to_json()))
            broadcast(snapshot)


def command_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, COMMAND_PORT))
    srv.listen()
    print(f"[mock_robot_core] command server on {HOST}:{COMMAND_PORT}")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=handle_command, args=(conn,), daemon=True).start()


def telemetry_server():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, TELEMETRY_PORT))
    srv.listen()
    print(f"[mock_robot_core] telemetry server on {HOST}:{TELEMETRY_PORT}")
    while True:
        conn, _ = srv.accept()
        with lock:
            telemetry_clients.append(conn)
            snapshot = runtime.telemetry_snapshot()
        print("[mock_robot_core] telemetry client connected")
        broadcast(snapshot)


def broadcast(messages):
    dead = []
    encoded = [(env.to_json() + "\n").encode("utf-8") for env in messages]
    with lock:
        for client in telemetry_clients:
            try:
                for line in encoded:
                    client.sendall(line)
            except OSError:
                dead.append(client)
        for client in dead:
            telemetry_clients.remove(client)


def telemetry_loop():
    while True:
        time.sleep(0.1)
        with lock:
            messages = runtime.tick()
        broadcast(messages)


if __name__ == "__main__":
    threading.Thread(target=command_server, daemon=True).start()
    threading.Thread(target=telemetry_server, daemon=True).start()
    telemetry_loop()
