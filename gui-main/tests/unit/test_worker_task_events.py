from robot_sim.application.workers.base import BaseWorker


def test_worker_progress_event_shape():
    worker = BaseWorker(task_kind='ik', task_id='task-1', correlation_id='corr-1')
    events = []
    worker.progress_event.connect(events.append)
    worker.emit_progress(stage='iterating', percent=25.0, message='step')
    assert events[0].task_id == 'task-1'
    assert events[0].task_kind == 'ik'
    assert events[0].correlation_id == 'corr-1'
    assert events[0].stage == 'iterating'
