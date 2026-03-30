from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from spine_ultrasound_ui.api_routes import (
    build_command_router,
    build_events_router,
    build_session_router,
    build_system_router,
    build_ws_router,
)
from spine_ultrasound_ui.services.api_command_guard import ApiCommandGuardService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


deployment_profile_service = DeploymentProfileService()
api_command_guard_service = ApiCommandGuardService(deployment_profile_service)

adapter = HeadlessAdapter(
    mode=os.getenv("SPINE_HEADLESS_BACKEND", os.getenv("SPINE_UI_BACKEND", "mock")),
    command_host=os.getenv("ROBOT_CORE_HOST", "127.0.0.1"),
    command_port=int(os.getenv("ROBOT_CORE_COMMAND_PORT", "5656")),
    telemetry_host=os.getenv("ROBOT_CORE_HOST", "127.0.0.1"),
    telemetry_port=int(os.getenv("ROBOT_CORE_TELEMETRY_PORT", "5657")),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing headless adapter...")
    adapter.start()
    yield
    logger.info("Tearing down headless adapter...")
    adapter.stop()


def _allowed_origins() -> list[str]:
    raw = os.getenv(
        "SPINE_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
    )
    origins = [item.strip() for item in raw.split(",") if item.strip()]
    return origins or ["http://localhost:5173"]


app = FastAPI(title="Spine Ultrasound Headless Adapter", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(build_system_router(lambda: adapter, lambda: deployment_profile_service))
app.include_router(build_session_router(lambda: adapter))
app.include_router(build_events_router(lambda: adapter))
app.include_router(build_command_router(lambda: adapter, lambda: api_command_guard_service))
app.include_router(build_ws_router(lambda: adapter))
