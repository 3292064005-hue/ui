from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from robot_sim.domain.errors import (
    CancelledTaskError,
    CollisionError,
    ExportRobotError,
    IKDidNotConvergeError,
    ImportRobotError,
    RobotSimError,
    SingularityError,
    ValidationError,
)


@dataclass(frozen=True)
class ErrorPresentation:
    """Structured error payload ready for GUI projection."""

    title: str
    user_message: str
    error_code: str
    severity: str = 'error'
    remediation_hint: str = ''
    log_payload: dict[str, object] = field(default_factory=dict)
    task_id: str = ''
    task_kind: str = ''
    correlation_id: str = ''
    stop_reason: str = ''


_ERROR_PRESENTATION_TABLE: dict[str, tuple[str, str]] = {
    ValidationError.default_error_code: ('输入或配置无效', 'warning'),
    IKDidNotConvergeError.default_error_code: ('逆运动学未收敛', 'warning'),
    SingularityError.default_error_code: ('奇异位形风险', 'warning'),
    CollisionError.default_error_code: ('碰撞约束冲突', 'warning'),
    ImportRobotError.default_error_code: ('机器人导入失败', 'error'),
    ExportRobotError.default_error_code: ('导出失败', 'error'),
    CancelledTaskError.default_error_code: ('任务已取消', 'info'),
}

_CANCEL_STOP_REASONS = {'cancelled', 'timeout', 'replaced'}


class TaskErrorMapper:
    """Canonical mapper that projects exceptions and worker-failure envelopes.

    This class is the single source of truth for presentation-layer error titles,
    severities, remediation hints, and log payload shaping.
    """

    def map_exception(self, exc: Exception) -> ErrorPresentation:
        """Project a Python exception into GUI presentation data.

        Args:
            exc: Exception raised by the active workflow.

        Returns:
            ErrorPresentation: Structured error payload.

        Raises:
            None: Exceptions are converted into presentation data.
        """
        if isinstance(exc, RobotSimError):
            return self._from_robot_sim_error(exc)
        return ErrorPresentation(
            title='内部异常',
            user_message=str(exc) or exc.__class__.__name__,
            error_code='unexpected_error',
            severity='error',
            remediation_hint='检查日志和输入参数后重试。',
            log_payload={'exception_type': exc.__class__.__name__},
        )

    def map_failed_event(self, event: object) -> ErrorPresentation:
        """Project a structured worker failure event into GUI presentation data.

        Args:
            event: Structured worker failure event emitted by the worker layer.

        Returns:
            ErrorPresentation: Structured error payload.

        Raises:
            None: Event payloads are normalized into presentation data.
        """
        error_code = str(getattr(event, 'error_code', '') or '')
        stop_reason = str(getattr(event, 'stop_reason', '') or '')
        if not error_code and stop_reason in _CANCEL_STOP_REASONS:
            error_code = CancelledTaskError.default_error_code
        title, severity = self._resolve_title_and_severity(error_code, stop_reason=stop_reason, fallback_severity=str(getattr(event, 'severity', '') or 'error'))
        remediation_hint = str(getattr(event, 'remediation_hint', '') or '')
        exception_type = str(getattr(event, 'exception_type', '') or 'Exception')
        message = str(getattr(event, 'message', '') or exception_type)
        metadata = dict(getattr(event, 'metadata', {}) or {})
        return ErrorPresentation(
            title=title,
            user_message=message,
            error_code=error_code or 'unexpected_error',
            severity=severity,
            remediation_hint=remediation_hint,
            log_payload=self._build_log_payload(
                error_code=error_code or 'unexpected_error',
                exception_type=exception_type,
                metadata=metadata,
                remediation_hint=remediation_hint,
            ),
            task_id=str(getattr(event, 'task_id', '') or ''),
            task_kind=str(getattr(event, 'task_kind', '') or ''),
            correlation_id=str(getattr(event, 'correlation_id', '') or ''),
            stop_reason=stop_reason,
        )

    def _from_robot_sim_error(self, exc: RobotSimError) -> ErrorPresentation:
        """Project a domain error into GUI presentation data.

        Args:
            exc: Domain-specific simulator error.

        Returns:
            ErrorPresentation: Structured error payload.

        Raises:
            None: Exceptions are converted into presentation data.
        """
        title, severity = self._resolve_title_and_severity(exc.error_code, stop_reason='', fallback_severity='error')
        return ErrorPresentation(
            title=title,
            user_message=exc.message or str(exc),
            error_code=exc.error_code,
            severity=severity,
            remediation_hint=exc.remediation_hint,
            log_payload=self._build_log_payload(
                error_code=exc.error_code,
                exception_type=exc.__class__.__name__,
                metadata=exc.metadata,
                remediation_hint=exc.remediation_hint,
            ),
        )

    @staticmethod
    def _build_log_payload(
        *,
        error_code: str,
        exception_type: str,
        metadata: Mapping[str, object],
        remediation_hint: str,
    ) -> dict[str, object]:
        """Build the structured log payload attached to projected errors.

        Args:
            error_code: Machine-readable error code.
            exception_type: Exception class name or failure envelope type name.
            metadata: Structured diagnostic metadata.
            remediation_hint: User-facing remediation hint.

        Returns:
            dict[str, object]: Serialized payload used by logging and diagnostics.

        Raises:
            None: Pure payload construction.
        """
        return {
            'error_code': str(error_code),
            'exception_type': str(exception_type),
            'metadata': dict(metadata),
            'remediation_hint': str(remediation_hint),
        }

    @staticmethod
    def _resolve_title_and_severity(error_code: str, *, stop_reason: str, fallback_severity: str) -> tuple[str, str]:
        """Resolve user-facing title and severity from canonical task-error metadata.

        Args:
            error_code: Machine-readable error code.
            stop_reason: Terminal stop reason emitted by the worker/orchestrator.
            fallback_severity: Default severity when the error code is unknown.

        Returns:
            tuple[str, str]: ``(title, severity)`` for presentation projection.

        Raises:
            None: Lookup-only helper.
        """
        normalized_code = str(error_code or '')
        if normalized_code in _ERROR_PRESENTATION_TABLE:
            return _ERROR_PRESENTATION_TABLE[normalized_code]
        if str(stop_reason or '') in _CANCEL_STOP_REASONS:
            return _ERROR_PRESENTATION_TABLE[CancelledTaskError.default_error_code]
        return '后台任务失败', str(fallback_severity or 'error')


class ExceptionPresentationMapper(TaskErrorMapper):
    """Backward-compatible alias for the canonical task-error mapper."""


__all__ = ['ErrorPresentation', 'TaskErrorMapper', 'ExceptionPresentationMapper']
