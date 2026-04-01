from __future__ import annotations
from enum import Enum


class JointType(str, Enum):
    REVOLUTE = "revolute"
    PRISMATIC = "prismatic"


class IKSolverMode(str, Enum):
    PINV = "pinv"
    DLS = "dls"
    LM = "lm"
    ANALYTIC_6R = "analytic_6r"


class SolverFamily(str, Enum):
    ITERATIVE = "iterative"
    ANALYTIC = "analytic"


class TrajectoryMode(str, Enum):
    JOINT = "joint_space"
    CARTESIAN = "cartesian_pose"


class PlannerFamily(str, Enum):
    JOINT = "joint"
    CARTESIAN = "cartesian"
    WAYPOINT_GRAPH = "waypoint_graph"


class ReferenceFrame(str, Enum):
    WORLD = "world"
    BASE = "base"
    LOCAL = "local"
    TOOL = "tool"


class CollisionLevel(str, Enum):
    NONE = "none"
    AABB = "aabb"
    CAPSULE = "capsule"
    MESH = "mesh"


class AppExecutionState(str, Enum):
    IDLE = "idle"
    ROBOT_READY = "robot_ready"
    SOLVING_IK = "solving_ik"
    PLANNING_TRAJECTORY = "planning_trajectory"
    PLAYING = "playing"
    BENCHMARKING = "benchmarking"
    EXPORTING = "exporting"
    ERROR = "error"


class TaskState(str, Enum):
    IDLE = 'idle'
    QUEUED = 'queued'
    RUNNING = 'running'
    CANCELLING = 'cancelling'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class ModuleStatus(str, Enum):
    STABLE = 'stable'
    EXPERIMENTAL = 'experimental'
    INTERNAL = 'internal'
    DEPRECATED = 'deprecated'


class ImporterFidelity(str, Enum):
    NATIVE = 'native'
    APPROXIMATE = 'approximate'
    SERIAL_KINEMATICS = 'serial_kinematics'
    SERIAL_WITH_VISUAL = 'serial_with_visual'
    SERIAL_WITH_COLLISION = 'serial_with_collision'


class KinematicConvention(str, Enum):
    DH = "dh"
    DH_APPROXIMATE_FROM_URDF = "dh_approximate_from_urdf"
