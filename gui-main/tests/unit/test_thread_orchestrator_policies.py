from robot_sim.presentation.thread_orchestrator import TaskHandle


def test_task_handle_has_correlation_id_default():
    task = TaskHandle(task_id='abc', task_kind='ik')
    assert task.task_id == 'abc'
    assert task.task_kind == 'ik'
    assert task.correlation_id == ''
