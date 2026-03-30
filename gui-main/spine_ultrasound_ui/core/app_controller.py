from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.core.alarm_manager import AlarmManager
from spine_ultrasound_ui.core.app_controller_config_mixin import AppControllerConfigMixin
from spine_ultrasound_ui.core.app_controller_runtime_mixin import AppControllerRuntimeMixin
from spine_ultrasound_ui.core.app_runtime_bridge import AppRuntimeBridge
from spine_ultrasound_ui.core.command_orchestrator import CommandOrchestrator
from spine_ultrasound_ui.core.control_plane_reader import ControlPlaneReader
from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.governance_coordinator import GovernanceCoordinator
from spine_ultrasound_ui.core.plan_service import LocalizationResult, PlanService
from spine_ultrasound_ui.core.postprocess_service import PostprocessService
from spine_ultrasound_ui.core.runtime_persistence_service import RuntimePersistenceService
from spine_ultrasound_ui.core.session_facade import SessionFacade
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.core.telemetry_store import TelemetryStore
from spine_ultrasound_ui.core.ui_projection_service import UiProjectionService
from spine_ultrasound_ui.core.view_state_factory import ViewStateFactory
from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig, ScanPlan, WorkflowArtifacts
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.services.bridge_observability_service import BridgeObservabilityService
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.config_service import ConfigService
from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.sdk_capability_service import SdkCapabilityService
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService
from spine_ultrasound_ui.services.session_governance_service import SessionGovernanceService
from spine_ultrasound_ui.services.runtime_verdict_kernel_service import RuntimeVerdictKernelService
from spine_ultrasound_ui.utils import ensure_dir


class AppController(AppControllerConfigMixin, AppControllerRuntimeMixin, QObject):
    status_updated = Signal(dict)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)
    experiments_updated = Signal(list)
    system_state_changed = Signal(str)
    alarm_raised = Signal(str)

    def __init__(self, root_dir: Path, backend: BackendBase):
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.exp_root = ensure_dir(self.root_dir / "experiments")
        self.runtime_dir = ensure_dir(self.root_dir / "runtime")
        self.backend = backend
        self.config_service = ConfigService()
        self.runtime_config_path = self.runtime_dir / "runtime_config.json"
        self.persistence = RuntimePersistenceService(
            config_service=self.config_service,
            runtime_config_path=self.runtime_config_path,
            ui_prefs_path=self.runtime_dir / "ui_preferences.json",
            session_meta_path=self.runtime_dir / "session_meta.json",
        )
        self.config = self.persistence.load_initial_config()
        self.telemetry = TelemetryStore()
        self.telemetry.metrics.pressure_target = self.config.pressure_target
        self.workflow_artifacts = WorkflowArtifacts()
        self.exp_manager = ExperimentManager(self.exp_root)
        self.session_service = SessionService(self.exp_manager)
        self.plan_service = PlanService()
        self.postprocess_service = PostprocessService(self.exp_manager)
        self.sdk_service = SdkCapabilityService()
        self.config_profile_service = ClinicalConfigService()
        self.sdk_runtime_service = SdkRuntimeAssetService()
        self.runtime_verdict_service = RuntimeVerdictKernelService()
        self.session_governance_service = SessionGovernanceService()
        self.bridge_observability_service = BridgeObservabilityService()
        self.deployment_profile_service = DeploymentProfileService()
        self.control_plane_snapshot_service = ControlPlaneSnapshotService()
        self.execution_scan_plan: Optional[ScanPlan] = None
        self.view_factory = ViewStateFactory(sdk_service=self.sdk_service)
        self.command_orchestrator = CommandOrchestrator(self.backend, self.session_service)
        self.governance = GovernanceCoordinator(
            sdk_service=self.sdk_service,
            config_service=self.config_profile_service,
            runtime_service=self.sdk_runtime_service,
            runtime_verdict_service=self.runtime_verdict_service,
            session_governance_service=self.session_governance_service,
            bridge_observability_service=self.bridge_observability_service,
            deployment_profile_service=self.deployment_profile_service,
            control_plane_snapshot_service=self.control_plane_snapshot_service,
        )
        self.session_facade = SessionFacade(self.session_service, self.exp_manager)
        self.ui_projection = UiProjectionService(self.view_factory)
        self.control_plane_reader = ControlPlaneReader(self.governance, self.ui_projection, self.get_persistence_snapshot)
        self.runtime_bridge = AppRuntimeBridge(self)
        snapshots = self.control_plane_reader.refresh(
            backend=self.backend,
            config=self.config,
            telemetry=self.telemetry,
            workflow_artifacts=self.workflow_artifacts,
            execution_scan_plan=self.execution_scan_plan,
            current_session_dir=self.session_service.current_session_dir,
            force_sdk_assets=True,
        )
        self.sdk_runtime_snapshot = dict(snapshots["sdk_runtime"])
        self.model_report = dict(snapshots["model_report"])
        self.config_report = dict(snapshots["config_report"])
        self.session_governance_snapshot = dict(snapshots["session_governance"])
        self.backend_link_snapshot = dict(snapshots["backend_link"])
        self.bridge_observability_snapshot = dict(snapshots["bridge_observability"])
        self.deployment_profile_snapshot = dict(snapshots["deployment_profile"])
        self.control_plane_snapshot = dict(snapshots["control_plane_snapshot"])
        self.alarm_manager = AlarmManager()
        self.experiments: list[ExperimentRecord] = []
        self.localization_result: Optional[LocalizationResult] = None
        self.preview_scan_plan: Optional[ScanPlan] = None
        self._connect_backend()
        self._connect_exception_handler()
