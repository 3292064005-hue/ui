"""
Spine Ultrasound Platform — Windows Development Mock Server
============================================================
Streams real webcam + synthetic ultrasound + 204-byte binary telemetry.
Gracefully falls back to synthetic frames when no camera is available.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio
import time
import struct
import math
import base64
import numpy as np
from loguru import logger

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("OpenCV not found — using synthetic camera frames")

app = FastAPI(title="Spine Ultrasound [WINDOWS DEV MOCK]")

# ═══════════════════════════════════════════════════
#  REST Endpoints for Button Actions
# ═══════════════════════════════════════════════════

scan_state = {"active": False, "session_id": None, "halted": False}

@app.post("/api/scan/start")
async def scan_start():
    scan_state["active"] = True
    scan_state["session_id"] = f"SES-{int(time.time())}"
    scan_state["halted"] = False
    logger.success(f"[REST] 扫描启动: {scan_state['session_id']}")
    return JSONResponse({"status": "ok", "session_id": scan_state["session_id"]})

@app.post("/api/scan/stop")
async def scan_stop():
    scan_state["active"] = False
    logger.info(f"[REST] 扫描停止: {scan_state['session_id']}")
    return JSONResponse({"status": "ok"})

@app.post("/api/estop")
async def estop():
    scan_state["active"] = False
    scan_state["halted"] = True
    logger.error("[REST] ⚠ 紧急制动已触发")
    return JSONResponse({"status": "halted"})

@app.get("/api/status")
async def get_status():
    return JSONResponse(scan_state)

# ═══════════════════════════════════════════════════
#  WebSocket: Binary Telemetry (204 bytes @ 60Hz)
# ═══════════════════════════════════════════════════

@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WS] 遥测通道已连接")
    try:
        while True:
            t = time.time()
            ts = int(t * 1000)

            # Simulated breathing force: 10N ± 0.5N sinusoidal
            force_z = 10.0 + math.sin(t * 3.0) * 0.5

            # Simulated 7-DOF joint angles (radians)
            joints = [
                math.sin(t * 0.3) * 0.8,          # J1 base
                math.cos(t * 0.5) * 0.4 + 0.5,    # J2 shoulder
                math.sin(t * 0.7) * 0.3 - 0.2,    # J3 elbow
                math.cos(t * 0.2) * 0.6,           # J4 wrist roll
                math.sin(t * 0.4) * 0.2,           # J5 wrist bend
                math.cos(t * 0.6) * 0.15,          # J6 wrist twist
                math.sin(t * 0.1) * 0.1,           # J7 flange
            ]

            fake_pose = [0.0] * 16  # 4x4 identity placeholder

            # 204-byte struct: q (8) + 16d (128) + d (8) + i (4) + 7d (56)
            payload = struct.pack('<q16ddi7d', ts, *fake_pose, force_z, 0, *joints)

            await websocket.send_bytes(payload)
            await asyncio.sleep(1 / 60.0)

    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.warning("[WS] 遥测通道断开")
    except Exception as e:
        logger.error(f"[WS] 遥测异常: {e}")

# ═══════════════════════════════════════════════════
#  WebSocket: RGB Camera (30 FPS, base64 JPEG)
# ═══════════════════════════════════════════════════

def generate_synthetic_camera_frame(t: float) -> bytes:
    """Generate a synthetic camera frame when no webcam is available."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Color bars
    colors = [(0,0,255), (0,255,0), (255,0,0), (0,255,255), (255,0,255), (255,255,0), (128,128,128), (255,255,255)]
    bar_w = 640 // len(colors)
    for i, c in enumerate(colors):
        frame[:, i*bar_w:(i+1)*bar_w] = c

    # Moving indicator
    cx = int(320 + math.sin(t) * 150)
    cv2.circle(frame, (cx, 240), 40, (0, 255, 255), 3)
    cv2.putText(frame, "SYNTHETIC CAMERA", (180, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    cv2.putText(frame, f"T={t:.1f}s", (cx - 30, 240 + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return base64.b64encode(buf).decode('utf-8')


@app.websocket("/ws/camera")
async def websocket_camera_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WS] RGB 摄像头通道已连接")

    cap = None
    use_real_cam = False

    if HAS_CV2:
        try:
            cap = cv2.VideoCapture(0)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                use_real_cam = True
                logger.success("[CAM] 真实摄像头已打开")
            else:
                logger.warning("[CAM] 摄像头无法打开，使用合成帧")
                cap.release()
                cap = None
        except Exception:
            logger.warning("[CAM] 摄像头初始化失败，使用合成帧")
            cap = None

    t_start = time.time()

    try:
        while True:
            t = time.time() - t_start

            if use_real_cam and cap is not None:
                ret, frame = cap.read()
                if not ret:
                    await asyncio.sleep(0.05)
                    continue

                h, w = frame.shape[:2]
                cv2.rectangle(frame, (w//2-50, h//2-50), (w//2+50, h//2+50), (0, 255, 255), 2)
                cv2.putText(frame, "ArUco Tracking", (w//2-60, h//2-60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                jpg_text = base64.b64encode(buffer).decode('utf-8')
            else:
                if HAS_CV2:
                    jpg_text = generate_synthetic_camera_frame(t)
                else:
                    await asyncio.sleep(1)
                    continue

            await websocket.send_text(jpg_text)
            await asyncio.sleep(1 / 30.0)

    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.warning("[WS] 摄像头通道断开")
    except Exception as e:
        logger.error(f"[WS] 摄像头异常: {e}")
    finally:
        if cap is not None:
            cap.release()

# ═══════════════════════════════════════════════════
#  WebSocket: Synthetic Ultrasound B-Mode (30 FPS)
# ═══════════════════════════════════════════════════

@app.websocket("/ws/ultrasound")
async def websocket_ultrasound_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WS] 超声 B-Mode 通道已连接")

    if not HAS_CV2:
        logger.warning("[US] OpenCV unavailable — ultrasound stream disabled")
        try:
            while True:
                await asyncio.sleep(5)
        except (WebSocketDisconnect, asyncio.CancelledError):
            return

    try:
        t = 0.0
        while True:
            # Generate cone-shaped B-mode noise
            noise = np.random.randint(15, 120, (480, 640), dtype=np.uint8)

            # Simulated bone shadow sweeping
            x_off = int(math.sin(t * 0.8) * 100) + 320
            y_off = int(math.cos(t * 0.5) * 30) + 250
            cv2.circle(noise, (x_off, y_off), 25, 0, -1)
            cv2.circle(noise, (x_off + 60, y_off + 15), 18, 0, -1)

            # Tissue layers (horizontal bands of varying brightness)
            for y_band in range(0, 480, 40):
                brightness = np.random.randint(5, 30)
                noise[y_band:y_band+3, :] = brightness

            us_frame = cv2.cvtColor(noise, cv2.COLOR_GRAY2BGR)

            # Cone mask
            mask = np.zeros((480, 640), dtype=np.uint8)
            pts = np.array([[320, 30], [80, 470], [560, 470]])
            cv2.fillPoly(mask, [pts], 255)
            final = cv2.bitwise_and(us_frame, us_frame, mask=mask)

            # Depth markers
            for d in range(1, 6):
                y = 30 + d * 80
                cv2.line(final, (90, y), (100, y), (0, 200, 200), 1)
                cv2.putText(final, f"{d*2}cm", (60, y+4), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 200, 200), 1)

            _, buffer = cv2.imencode('.jpg', final, [cv2.IMWRITE_JPEG_QUALITY, 65])
            jpg_text = base64.b64encode(buffer).decode('utf-8')

            await websocket.send_text(jpg_text)
            t += 0.05
            await asyncio.sleep(1 / 30.0)

    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.warning("[WS] 超声通道断开")
    except Exception as e:
        logger.error(f"[WS] 超声异常: {e}")

# ═══════════════════════════════════════════════════
#  WebSocket: Point Cloud (placeholder)
# ═══════════════════════════════════════════════════

@app.websocket("/ws/pointcloud")
async def websocket_pointcloud_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WS] 点云通道已连接")
    try:
        while True:
            await asyncio.sleep(2.0)
            mock_point = b'\x00\x00\xff\x7f' * 300
            await websocket.send_bytes(mock_point)
    except (WebSocketDisconnect, asyncio.CancelledError):
        logger.warning("[WS] 点云通道断开")
    except Exception as e:
        logger.error(f"[WS] 点云异常: {e}")


# ═══════════════════════════════════════════════════
#  Main Entry
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    logger.success("=" * 56)
    logger.success("  脊柱超声机器人 · Windows 开发模拟服务器")
    logger.success("  (Open3D / TensorRT / C++ Core 已禁用)")
    logger.success("=" * 56)
    uvicorn.run(app, host="0.0.0.0", port=8000)
