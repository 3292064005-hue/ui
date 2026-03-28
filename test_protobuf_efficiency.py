#!/usr/bin/env python3
"""
Test script for Protobuf IPC efficiency
"""

import time
import json

# Mock protobuf-like serialization for testing
def serialize_json(cmd):
    return json.dumps(cmd).encode('utf-8')

def serialize_protobuf_mock(cmd):
    # Mock protobuf: length prefix + compact binary
    data = f"{cmd['protocol_version']}|{cmd['command']}|{cmd['payload']}|{cmd['request_id']}".encode('utf-8')
    length = len(data).to_bytes(4, 'big')
    return length + data

def benchmark_serialization():
    cmd = {
        "protocol_version": 1,
        "command": "start_scan",
        "payload": '{"scan_speed": 8.0}',
        "request_id": 12345
    }

    # JSON benchmark
    start = time.time()
    for _ in range(10000):
        data = serialize_json(cmd)
    json_time = time.time() - start
    json_size = len(serialize_json(cmd))

    # Protobuf mock benchmark
    start = time.time()
    for _ in range(10000):
        data = serialize_protobuf_mock(cmd)
    pb_time = time.time() - start
    pb_size = len(serialize_protobuf_mock(cmd))

    print("Serialization Benchmark:")
    print(f"JSON: {json_time:.4f}s, size: {json_size} bytes")
    print(f"Protobuf: {pb_time:.4f}s, size: {pb_size} bytes")
    print(f"Improvement: {json_time/pb_time:.2f}x faster, {json_size/pb_size:.2f}x smaller")

if __name__ == "__main__":
    benchmark_serialization()