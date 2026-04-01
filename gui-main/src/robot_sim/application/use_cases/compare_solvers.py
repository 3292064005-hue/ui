from __future__ import annotations

from robot_sim.domain.enums import IKSolverMode


class CompareSolversUseCase:
    def __init__(self, run_ik_uc, solver_ids: list[str] | None = None) -> None:
        self._run_ik_uc = run_ik_uc
        self._solver_ids = solver_ids or list(getattr(run_ik_uc, 'solver_ids', ['pinv', 'dls']))

    def execute(self, req):
        rows: list[dict[str, object]] = []
        for solver_id in self._solver_ids:
            solver_value = str(solver_id)
            try:
                mode = IKSolverMode(solver_value)
            except ValueError:
                mode = solver_value
            cfg = type(req.config)(**{**req.config.__dict__, 'mode': mode})
            result = self._run_ik_uc.execute(type(req)(spec=req.spec, target=req.target, q0=req.q0, config=cfg))
            rows.append({
                'solver_id': solver_id,
                'success': bool(result.success),
                'final_pos_err': float(result.final_pos_err),
                'final_ori_err': float(result.final_ori_err),
                'elapsed_ms': float(result.elapsed_ms),
                'stop_reason': result.stop_reason,
                'effective_mode': result.effective_mode,
            })
        return rows
