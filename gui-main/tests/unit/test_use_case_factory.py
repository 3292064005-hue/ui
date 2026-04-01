from __future__ import annotations

from robot_sim.app.use_case_factory import build_use_case_bundle
from robot_sim.core.ik.registry import SolverRegistry
from robot_sim.core.trajectory.registry import TrajectoryPlannerRegistry
from robot_sim.application.registries.importer_registry import ImporterRegistry
from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.application.services.export_service import ExportService
from robot_sim.application.services.package_service import PackageService
from robot_sim.application.services.playback_service import PlaybackService


class DummyExporter(ExportService):
    def __init__(self):
        pass


class DummyPackageService(PackageService):
    def __init__(self):
        pass


def test_build_use_case_bundle_constructs_expected_use_cases(tmp_path):
    bundle = build_use_case_bundle(
        solver_registry=SolverRegistry(),
        planner_registry=TrajectoryPlannerRegistry(),
        importer_registry=ImporterRegistry(),
        benchmark_service=BenchmarkService(run_ik_uc=object()),
        export_service=DummyExporter(),
        package_service=DummyPackageService(),
        playback_service=PlaybackService(),
    )
    assert bundle.fk_uc is not None
    assert bundle.ik_uc is not None
    assert bundle.traj_uc is not None
    assert bundle.import_robot_uc is not None
