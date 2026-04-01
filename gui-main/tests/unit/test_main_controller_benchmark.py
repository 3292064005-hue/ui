from __future__ import annotations

from robot_sim.app.container import build_container
from robot_sim.presentation.main_controller import MainController


def test_main_controller_runs_and_exports_benchmark(project_root):
    controller = MainController(project_root, container=build_container(project_root))
    controller.load_robot('planar_2dof')
    report = controller.run_benchmark()
    assert report.num_cases >= 5
    json_path = controller.export_benchmark('bench_test.json')
    csv_path = controller.export_benchmark_cases_csv('bench_test.csv')
    assert json_path.exists()
    assert csv_path.exists()
