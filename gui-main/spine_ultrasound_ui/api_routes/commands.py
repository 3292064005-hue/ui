from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Body, Header, HTTPException
from loguru import logger

from spine_ultrasound_ui.services.api_command_guard import ApiCommandHeaders


def build_command_router(adapter_getter: Callable[[], Any], guard_getter: Callable[[], Any]) -> APIRouter:
    router = APIRouter()

    @router.post("/api/v1/commands/{command}")
    async def post_command(
        command: str,
        payload: Any = Body(default=None),
        x_spine_role: str | None = Header(default=None),
        x_spine_actor: str | None = Header(default=None),
        x_spine_workspace: str | None = Header(default=None),
        x_spine_lease_id: str | None = Header(default=None),
        x_spine_intent: str | None = Header(default=None),
        x_spine_session_id: str | None = Header(default=None),
        x_spine_api_token: str | None = Header(default=None),
    ):
        adapter = adapter_getter()
        guard = guard_getter()
        try:
            payload_dict = guard.normalize_payload(
                adapter=adapter,
                command=command,
                payload=payload,
                headers=ApiCommandHeaders(
                    role=x_spine_role,
                    actor=x_spine_actor,
                    workspace=x_spine_workspace,
                    lease_id=x_spine_lease_id,
                    intent=x_spine_intent,
                    session_id=x_spine_session_id,
                    api_token=x_spine_api_token,
                ),
            )
            return adapter.command(command, payload_dict)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(f"Headless command failure for {command}: {exc}")
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return router
