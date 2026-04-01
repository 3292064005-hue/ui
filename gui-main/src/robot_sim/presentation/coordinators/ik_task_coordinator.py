from __future__ import annotations

import numpy as np

from robot_sim.application.workers.ik_worker import IKWorker
from robot_sim.presentation.coordinators._helpers import require_dependency, require_view, run_presented, set_plot_curves


class IKTaskCoordinator:
    """Own the IK task orchestration previously embedded in the window shell."""

    def __init__(self, window, *, solver=None, threader=None) -> None:
        self.window = window
        self.solver = require_dependency(solver if solver is not None else getattr(window, 'solver_facade', None), 'solver_facade')
        self.threader = require_dependency(threader if threader is not None else getattr(window, 'threader', None), 'threader')

    def run(self) -> None:
        """Public UI entrypoint for starting an IK task."""
        self.start_task()

    def start_task(self) -> None:
        """Start the IK worker using the shared background-thread orchestrator."""
        def action() -> None:
            req = require_view(self.window, 'read_ik_request')
            ik_use_case = require_dependency(getattr(self.solver, 'ik_use_case', None), 'solver_facade.ik_use_case')
            worker = IKWorker(req, ik_use_case)
            self.window._pending_ik_request = req
            require_view(self.window, 'project_task_started', 'ik', 'IK 任务已启动')
            task = self.threader.start(
                worker=worker,
                on_progress=self.window.on_ik_progress,
                on_finished=self.window.on_ik_finished,
                on_failed=self.window.on_worker_failed,
                on_cancelled=self.window.on_worker_cancelled,
                task_kind='ik',
            )
            require_view(self.window, 'project_task_registered', task.task_id, task.task_kind)

        run_presented(self.window, action, title='错误')

    def handle_finished(self, result) -> None:
        """Project a completed IK result into the presentation state and widgets."""
        require_view(self.window, 'project_busy_state', False, '')

        def action() -> None:
            self.solver.apply_ik_result(self.window._pending_ik_request, result)
            summary = self.window.metrics_service.summarize_ik(result)
            require_view(self.window, 'project_ik_result', result, summary)
            if result.logs:
                x = np.array([log.iter_idx + log.attempt_idx * 1e-3 for log in result.logs], dtype=float)
                set_plot_curves(
                    self.window,
                    'ik_error',
                    (
                        ('position_error', x, np.array([log.pos_err_norm for log in result.logs], dtype=float)),
                        ('orientation_error', x, np.array([log.ori_err_norm for log in result.logs], dtype=float)),
                    ),
                    clear_first=True,
                )
                set_plot_curves(
                    self.window,
                    'condition',
                    (
                        ('condition_number', x, np.array([log.cond_number for log in result.logs], dtype=float)),
                        ('manipulability', x, np.array([log.manipulability for log in result.logs], dtype=float)),
                    ),
                    clear_first=True,
                )

        run_presented(self.window, action, title='错误')
