from robot_sim.domain.errors import (
    CancelledTaskError,
    CollisionError,
    ExportRobotError,
    IKDidNotConvergeError,
    ImportRobotError,
    IncompatibleSchemaError,
    RobotSimError,
    SingularityError,
    UnreachableTargetError,
    ValidationError,
)


def test_error_taxonomy_inherits_from_base_error():
    for cls in [
        ValidationError,
        UnreachableTargetError,
        IKDidNotConvergeError,
        SingularityError,
        CollisionError,
        ImportRobotError,
        ExportRobotError,
        CancelledTaskError,
        IncompatibleSchemaError,
    ]:
        assert issubclass(cls, RobotSimError)


def test_ik_non_convergence_is_unreachable_subtype():
    assert issubclass(IKDidNotConvergeError, UnreachableTargetError)
