from __future__ import annotations

from robot_sim.application.services.config_service import ConfigService
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.run_benchmark import RunBenchmarkUseCase
from robot_sim.application.use_cases.run_fk import RunFKUseCase
from robot_sim.application.use_cases.run_ik import RunIKUseCase
from robot_sim.application.services.benchmark_service import BenchmarkService
from robot_sim.core.ik.registry import DefaultSolverRegistry
from robot_sim.model.session_state import SessionState
from robot_sim.presentation.controllers.benchmark_controller import BenchmarkController
from robot_sim.presentation.controllers.ik_controller import IKController
from robot_sim.presentation.state_store import StateStore


def test_benchmark_controller_builds_config_and_runs(project_root):
    state = StateStore(SessionState())
    config_service = ConfigService(project_root / 'configs')
    registry = RobotRegistry(project_root / 'configs' / 'robots')
    spec = registry.load('planar_2dof')
    fk = RunFKUseCase().execute(type('FKReq', (), {'spec': spec, 'q': spec.home_q.copy()})())
    state.patch(robot_spec=spec, q_current=spec.home_q.copy(), fk_result=fk)
    ik_uc = RunIKUseCase(DefaultSolverRegistry())
    bench_uc = RunBenchmarkUseCase(BenchmarkService(ik_uc))
    ik_ctrl = IKController(state, config_service.load_solver_config()['ik'], RunFKUseCase(), ik_uc)
    bench_ctrl = BenchmarkController(state, bench_uc, ik_ctrl.build_ik_request)
    config = bench_ctrl.build_benchmark_config(mode='dls')
    report = bench_ctrl.run_benchmark(config)
    assert config.mode.value == 'dls'
    assert report.num_cases >= 5
