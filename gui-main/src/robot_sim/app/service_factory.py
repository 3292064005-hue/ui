from __future__ import annotations

from pathlib import Path

from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.services.capability_service import CapabilityService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.metrics_service import MetricsService
from robot_sim.application.services.module_status_service import ModuleStatusService
from robot_sim.application.services.runtime_feature_service import RuntimeFeatureService
from robot_sim.application.services.package_service import PackageService
from robot_sim.application.services.playback_service import PlaybackService


def build_metrics_service() -> MetricsService:
    """Construct the metrics service.

    Returns:
        MetricsService: Fresh metrics helper.

    Raises:
        None: Stateless constructor.
    """
    return MetricsService()


def build_export_service(export_root: str | Path) -> ExportService:
    """Construct the export service rooted at an explicit writable directory.

    Args:
        export_root: Writable export directory.

    Returns:
        ExportService: Export service bound to ``export_root``.

    Raises:
        OSError: Propagates directory creation failures from ``ExportService``.
    """
    return ExportService(Path(export_root))


def build_playback_service() -> PlaybackService:
    """Construct the playback service.

    Returns:
        PlaybackService: Stateless playback helper.

    Raises:
        None: Stateless constructor.
    """
    return PlaybackService()


def build_package_service(export_root: str | Path) -> PackageService:
    """Construct the package service rooted at an explicit writable directory.

    Args:
        export_root: Writable export directory.

    Returns:
        PackageService: Package service bound to ``export_root``.

    Raises:
        OSError: Propagates directory creation failures from ``PackageService``.
    """
    return PackageService(Path(export_root))


def build_benchmark_service(ik_uc) -> BenchmarkService:
    return BenchmarkService(ik_uc)


def build_capability_service(*, runtime_feature_policy=None) -> CapabilityService:
    return CapabilityService(runtime_feature_policy=runtime_feature_policy)


def build_module_status_service(*, runtime_feature_policy=None) -> ModuleStatusService:
    return ModuleStatusService(runtime_feature_policy=runtime_feature_policy)


def build_runtime_feature_service(config_service) -> RuntimeFeatureService:
    return RuntimeFeatureService(config_service)
