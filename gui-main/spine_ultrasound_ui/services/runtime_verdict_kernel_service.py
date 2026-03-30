from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.xmate_model_service import XMateModelService


class RuntimeVerdictKernelService:
    """Resolve the sole compile/precheck verdict from the runtime contract kernel.

    The desktop may still compute an advisory application-side approximation for
    operator context, but it must not overrule a runtime/core provided verdict.
    """

    def __init__(self, advisory_model_service: XMateModelService | None = None) -> None:
        self.advisory_model_service = advisory_model_service or XMateModelService()

    def resolve(self, backend: Any, plan: ScanPlan | None, config: RuntimeConfig) -> dict[str, Any]:
        advisory = self.advisory_model_service.build_report(plan, config)
        runtime_verdict = self._query_runtime_verdict(backend, plan, config)
        if runtime_verdict:
            return self._normalize_runtime_verdict(runtime_verdict, advisory)
        return self._build_advisory_fallback(advisory)

    def _query_runtime_verdict(self, backend: Any, plan: ScanPlan | None, config: RuntimeConfig) -> dict[str, Any]:
        if backend is None or not hasattr(backend, 'get_final_verdict'):
            return {}
        try:
            verdict = backend.get_final_verdict(plan, config)
        except TypeError:
            verdict = backend.get_final_verdict(plan)
        except Exception:
            return {}
        return dict(verdict or {})

    @staticmethod
    def _normalize_runtime_verdict(runtime_verdict: dict[str, Any], advisory: dict[str, Any]) -> dict[str, Any]:
        payload = dict(runtime_verdict)
        final_verdict = dict(payload.get('final_verdict', {}))
        blockers = list(payload.get('blockers', []))
        warnings = list(payload.get('warnings', []))
        summary_state = str(payload.get('summary_state') or ('blocked' if final_verdict.get('accepted') is False else 'ready'))
        payload.setdefault('summary_state', summary_state)
        payload.setdefault('summary_label', str(advisory.get('summary_label') or {
            'ready': '模型前检通过',
            'warning': '模型前检告警',
            'blocked': '模型前检阻塞',
            'idle': '未生成路径',
        }.get(summary_state, '模型前检')))
        payload.setdefault('detail', str(final_verdict.get('reason') or advisory.get('detail', '')))
        payload['warnings'] = warnings
        payload['blockers'] = blockers
        payload['final_verdict'] = {
            'accepted': bool(final_verdict.get('accepted', summary_state != 'blocked')),
            'reason': str(final_verdict.get('reason') or payload.get('detail', '')),
            'evidence_id': str(final_verdict.get('evidence_id', '')),
            'expected_state_delta': final_verdict.get('expected_state_delta', {}),
            'policy_state': str(final_verdict.get('policy_state', summary_state)),
            'source': str(final_verdict.get('source') or payload.get('authority_source', 'cpp_robot_core')),
            'advisory_only': False,
        }
        payload.setdefault('authority_source', str(payload['final_verdict'].get('source') or 'cpp_robot_core'))
        payload.setdefault('verdict_kind', 'final')
        payload.setdefault('approximate', False)
        payload.setdefault('advisory_python', advisory)
        payload.setdefault('model_contract', dict(advisory.get('model_contract', {})))
        payload.setdefault('envelope', dict(advisory.get('envelope', {})))
        payload.setdefault('dh_parameters', list(advisory.get('dh_parameters', [])))
        payload.setdefault('plan_metrics', dict(advisory.get('plan_metrics', {})))
        payload.setdefault('execution_selection', dict(advisory.get('execution_selection', {})))
        return payload

    @staticmethod
    def _build_advisory_fallback(advisory: dict[str, Any]) -> dict[str, Any]:
        payload = dict(advisory)
        accepted = str(payload.get('summary_state', 'idle')) not in {'blocked'}
        payload['authority_source'] = 'python_advisory_fallback'
        payload['verdict_kind'] = 'advisory'
        payload['approximate'] = True
        payload['final_verdict'] = {
            'accepted': accepted,
            'reason': str(payload.get('detail', '')),
            'evidence_id': '',
            'expected_state_delta': {
                'next_state': 'ready_for_lock' if accepted else 'plan_rework_required',
            },
            'policy_state': str(payload.get('summary_state', 'idle')),
            'source': 'python_advisory_fallback',
            'advisory_only': True,
        }
        payload.setdefault('advisory_python', dict(advisory))
        return payload
