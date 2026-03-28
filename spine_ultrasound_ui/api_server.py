from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn
from contextlib import asynccontextmanager

from core.memory_pool import PreAllocatedRingBuffer
from core.ipc_client import ZeroCopyIpcClient
from ws_broadcaster import WebSocketBroadcaster
# from services.webrtc_streamer import WebRTCStreamer

# Global Application State
memory_pool = PreAllocatedRingBuffer(capacity_frames=300000)
ipc_client = ZeroCopyIpcClient(memory_pool, address="tcp://127.0.0.1:5555")
broadcaster = WebSocketBroadcaster(memory_pool)
# webrtc = WebRTCStreamer() # Nvenc Pipeline 

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Events
    logger.info("Initializing Headless UI Backend...")
    ipc_client.start()
    broadcaster.start_background_task()
    # webrtc.start_stream()
    
    yield
    
    # Teardown Events
    logger.info("Tearing down System gracefully...")
    broadcaster.stop()
    ipc_client.stop()
    # webrtc.stop()

# Initialize FastAPI App
app = FastAPI(title="Spine Ultrasound Headless Platform", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since it's a closed robotics network
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====== WebSocket Routes ======
@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    """ Exposes 60Hz Binary ArrayBuffers from 'cpp_robot_core' instantly """
    await broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive waiting for client commands (e.g. Pause Request)
            incoming = await websocket.receive_bytes()
            # if len(incoming) == ? -> forward to cpp_robot_core logic
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)

# ====== REST API Routes ======
@app.get("/api/v1/status")
async def get_system_status():
    return {
        "memory_pool_capacity": memory_pool.capacity,
        "robot_connected": ipc_client.is_running,
        "fps": 60,
    }

# WebRTC Signaling Endpoint
@app.post("/api/v1/webrtc/offer")
async def webrtc_offer(offer: dict):
    # sdp, type = offer["sdp"], offer["type"]
    # We would pass the offer to aiortc and return the answer
    return {"status": "placeholder_for_aiortc_nvenc_answer"}
    
if __name__ == "__main__":
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
