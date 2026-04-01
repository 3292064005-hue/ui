from robot_sim.domain.enums import TaskState
from robot_sim.model.task_snapshot import TaskSnapshot


def test_task_snapshot_state_property():
    snapshot = TaskSnapshot(task_id='t1', task_kind='ik', task_state=TaskState.RUNNING, progress_stage='iter', progress_percent=12.5)
    assert snapshot.state == 'running'
    assert snapshot.progress_percent == 12.5
