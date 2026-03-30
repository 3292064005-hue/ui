from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_control_plane_service import BackendControlPlaneService
from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService


class HeadlessControlPlaneAggregator:
    def __init__(
        self,
        backend_control_plane_service: BackendControlPlaneService | None = None,
        deployment_profile_service: DeploymentProfileService | None = None,
        control_plane_snapshot_service: ControlPlaneSnapshotService | None = None,
    ) -> None:
        self.backend_control_plane_service = backend_control_plane_service or BackendControlPlaneService()
        self.deployment_profile_service = deployment_profile_service or DeploymentProfileService()
        self.control_plane_snapshot_service = control_plane_snapshot_service or ControlPlaneSnapshotService()

    def build(
        self,
        *,
        local_config: RuntimeConfig,
        runtime_config: dict[str, Any],
        schema: dict[str, Any],
        status: dict[str, Any],
        health: dict[str, Any],
        topic_catalog: dict[str, Any],
        recent_commands: list[dict[str, Any]],
        control_authority: dict[str, Any],
        session_governance: dict[str, Any] | None = None,
        evidence_seal: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        deployment_profile = self.deployment_profile_service.build_snapshot(local_config)
        control_plane = self.backend_control_plane_service.build(
            local_config=local_config,
            runtime_config=runtime_config,
            schema=schema,
            status=status,
            health=health,
            topic_catalog=topic_catalog,
            recent_commands=recent_commands,
            control_authority=control_authority,
        )
        backend_link = {
            "summary_state": control_plane.get("summary_state", "unknown"),
            "summary_label": control_plane.get("summary_label", "control plane"),
            "detail": control_plane.get("detail", ""),
            "blockers": control_plane.get("blockers", []),
            "warnings": control_plane.get("warnings", []),
            "telemetry_stale": bool(health.get("telemetry_stale", False)),
            "latest_telemetry_age_ms": health.get("latest_telemetry_age_ms"),
            "control_plane": control_plane,
        }
        unified = self.control_plane_snapshot_service.build(
            backend_link=backend_link,
            control_authority=control_authority,
            deployment_profile=deployment_profile,
            bridge_observability={
                "summary_state": "blocked" if bool(health.get("telemetry_stale", False)) else "ready",
                "summary_label": "bridge observability" if not bool(health.get("telemetry_stale", False)) else "bridge stale",
                "detail": f"latest_telemetry_age_ms={health.get('latest_telemetry_age_ms', 'unknown')}",
            },
            session_governance=session_governance,
            evidence_seal=evidence_seal,
            release_mode=deployment_profile.get("name", "dev"),
        )
        return {
            **control_plane,
            "deployment_profile": deployment_profile,
            "unified_snapshot": unified,
            "control_plane_snapshot": unified,
        }
