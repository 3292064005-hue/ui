from __future__ import annotations

from robot_sim.app.bootstrap import get_project_root
from robot_sim.app.container import build_container
from robot_sim.model.solver_config import IKConfig


def test_benchmark_use_case_emits_v7_suite_metadata():
    container = build_container(get_project_root())
    spec = container.robot_registry.load('planar_2dof')
    report = container.benchmark_uc.execute(spec, IKConfig())
    assert report.num_cases > 0
    assert report.metadata['suite_metadata']['pack_version'] == 'v7'
