from __future__ import annotations

from typing import Mapping


class RobotSimError(Exception):
    """Base error for the simulator with machine-readable metadata."""

    default_error_code = 'robot_sim_error'
    default_remediation_hint = ''

    def __init__(
        self,
        message: str = '',
        *,
        error_code: str | None = None,
        remediation_hint: str | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> None:
        self.message = str(message)
        self.error_code = str(error_code or self.default_error_code)
        self.remediation_hint = str(remediation_hint or self.default_remediation_hint)
        self.metadata = dict(metadata or {})
        super().__init__(self.__str__())

    def to_dict(self) -> dict[str, object]:
        return {
            'message': self.message,
            'error_code': self.error_code,
            'remediation_hint': self.remediation_hint,
            'metadata': dict(self.metadata),
        }

    def __str__(self) -> str:
        parts = [self.message] if self.message else []
        if self.error_code:
            parts.append(f'[{self.error_code}]')
        if self.remediation_hint:
            parts.append(f'hint={self.remediation_hint}')
        return ' '.join(parts) or self.__class__.__name__


class ValidationError(RobotSimError):
    """Raised when model or input validation fails."""

    default_error_code = 'validation_error'
    default_remediation_hint = '检查输入参数、配置文件和关节限位。'


class UnreachableTargetError(RobotSimError):
    """Raised when the requested target pose or path is outside the reachable workspace."""

    default_error_code = 'unreachable_target'
    default_remediation_hint = '调整目标位姿、初始解或工作空间边界。'


class IKDidNotConvergeError(UnreachableTargetError):
    """Raised when IK stops without meeting tolerances."""

    default_error_code = 'ik_did_not_converge'
    default_remediation_hint = '尝试切换求解器、增大迭代次数或更换初值。'


class SingularityError(RobotSimError):
    """Raised when a solve or update is blocked by singular kinematics."""

    default_error_code = 'singularity_detected'
    default_remediation_hint = '远离奇异位形，或切换到带阻尼的求解模式。'


class CollisionError(RobotSimError):
    """Raised when scene validation rejects a state or trajectory because of collision."""

    default_error_code = 'collision_detected'
    default_remediation_hint = '检查规划场景、允许碰撞矩阵和轨迹可行性。'


class ImportRobotError(RobotSimError):
    """Raised when a robot description cannot be imported safely."""

    default_error_code = 'robot_import_failed'
    default_remediation_hint = '确认机器人文件格式正确，并检查导入器保真度边界。'


class ExportRobotError(RobotSimError):
    """Raised when a report, bundle, or session cannot be exported."""

    default_error_code = 'robot_export_failed'
    default_remediation_hint = '检查导出目录权限、依赖安装情况和输出路径。'


class CancelledTaskError(RobotSimError):
    """Raised when a long-running task is cancelled before completion."""

    default_error_code = 'task_cancelled'
    default_remediation_hint = '重新提交任务，或等待当前任务释放资源后重试。'


class IncompatibleSchemaError(RobotSimError):
    """Raised when serialized data does not match the supported schema contract."""

    default_error_code = 'incompatible_schema'
    default_remediation_hint = '升级/迁移导出文件，或使用匹配版本重新生成。'


__all__ = [
    'RobotSimError',
    'ValidationError',
    'UnreachableTargetError',
    'IKDidNotConvergeError',
    'SingularityError',
    'CollisionError',
    'ImportRobotError',
    'ExportRobotError',
    'CancelledTaskError',
    'IncompatibleSchemaError',
]
