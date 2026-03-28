import asyncio
import struct
import numpy as np
from typing import List
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from .core.memory_pool import PreAllocatedRingBuffer

class WebSocketBroadcaster:
    """
    Subsamples the 1kHz memory_pool at 60Hz and pushes raw binary ArrayBuffers to the browser.
    Completely zero-copy payload. We never serialize to JSON.
    """
    def __init__(self, memory_pool: PreAllocatedRingBuffer):
        self.active_connections: List[WebSocket] = []
        self.pool = memory_pool
        self.running = False
        self._task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Frontend HMI connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Frontend HMI disconnected: {websocket.client}")

    async def pump_telemetry_loop(self):
        """ Runs at exactly 60 Hz to match Browser requestAnimationFrame limit """
        self.running = True
        logger.info("[Broadcaster] 60FPS Binary Telemetry Pump started.")
        
        while self.running:
            if not self.active_connections:
                await asyncio.sleep(0.5)
                continue
                
            # Get latest from pool (Index: head - 1)
            idx = (self.pool.head - 1) % self.pool.capacity
            
            # Fetch arrays (zero copy lookup)
            ts = self.pool.timestamps_ns[idx]
            pose = self.pool.tcp_poses[idx]    # shape (16,)
            force = self.pool.forces_z[idx]    # scalar
            safety = self.pool.safety_statuses[idx] # scalar

            # Pack it precisely matching the C-Struct defined previously
            # Format: "=q 16d d i" (8 + 128 + 8 + 4 = 148 Bytes)
            binary_payload = struct.pack("=q16ddi", int(ts), *pose, float(force), int(safety))

            for ws in self.active_connections:
                try:
                    # Async broadcast bytes (Received as ArrayBuffer in JS)
                    await ws.send_bytes(binary_payload)
                except TimeoutError:
                    self.disconnect(ws)
                except Exception:
                    self.disconnect(ws)

            # Cap frame rate ~60Hz to protect DOM
            await asyncio.sleep(0.016)

    def start_background_task(self):
        self._task = asyncio.create_task(self.pump_telemetry_loop())

    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
