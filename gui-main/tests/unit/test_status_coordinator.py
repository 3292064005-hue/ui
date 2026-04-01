from types import SimpleNamespace

from robot_sim.domain.enums import TaskState
from robot_sim.model.task_snapshot import TaskSnapshot
from robot_sim.presentation.coordinators.status_coordinator import StatusCoordinator


class DummyStore:
    def __init__(self):
        self.snapshot = None
        self.error = None
        self.app_state = None

    def patch_task(self, snapshot):
        self.snapshot = snapshot

    def patch_error(self, error):
        self.error = error

    def patch(self, **kwargs):
        self.app_state = kwargs.get('app_state')


class DummyStatusPanel:
    def __init__(self):
        self.kwargs = None

    def set_metrics(self, **kwargs):
        self.kwargs = kwargs


class DummyWindow:
    def __init__(self):
        self.controller = SimpleNamespace(
            state_store=DummyStore(),
            task_error_mapper=SimpleNamespace(
                map_failed_event=lambda failure: SimpleNamespace(title='Worker failed', user_message=str(getattr(failure, 'message', 'x'))),
                map_exception=lambda exc: SimpleNamespace(title='Exception', user_message=str(exc)),
            ),
        )
        self.runtime_facade = SimpleNamespace(
            state_store=self.controller.state_store,
            task_error_mapper=SimpleNamespace(
                map_failed_event=lambda failure: SimpleNamespace(title='Worker failed', user_message=getattr(failure, 'message', str(failure))),
                map_exception=lambda exc: SimpleNamespace(title='Worker failed', user_message=str(exc)),
            ),
        )
        self.status_panel = DummyStatusPanel()
        self._show = []
        self.project_task_snapshot = self._project_task_snapshot
        self.project_worker_failure = self._project_worker_failure

    def _project_task_snapshot(self, snapshot):
        self.controller.state_store.patch_task(snapshot)
        self.status_panel.set_metrics(playback='idle')

    def _project_worker_failure(self, presentation):
        self.controller.state_store.patch_error(presentation)
        self._show.append((presentation.title, presentation.user_message))


def test_status_coordinator_patches_state_store_and_projects_failures():
    window = DummyWindow()
    coord = StatusCoordinator(window)
    snap = TaskSnapshot(task_id='t', task_kind='ik', task_state=TaskState.RUNNING)
    coord.apply_task_snapshot(snap)
    failure = SimpleNamespace(message='boom', error_code='unexpected_error')
    coord.handle_worker_failure(failure)
    assert window.controller.state_store.snapshot is snap
    assert window.status_panel.kwargs == {'playback': 'idle'}
    assert window._show == [('Worker failed', 'boom')]
