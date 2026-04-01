from __future__ import annotations

from robot_sim.domain.runtime_contracts import MODULE_STATUSES, render_module_status_markdown


class ModuleStatusService:
    """Provide module-status snapshots for presentation and diagnostics."""

    MODULE_STATUSES: dict[str, str] = MODULE_STATUSES

    def __init__(self, runtime_feature_policy=None) -> None:
        self._runtime_feature_policy = runtime_feature_policy

    def snapshot(self) -> dict[str, str]:
        """Return the current module-status snapshot.

        Returns:
            dict[str, str]: Module identifier to module-status mapping.

        Raises:
            None: The snapshot is static runtime metadata.
        """
        return dict(self.MODULE_STATUSES)

    def snapshot_details(self) -> dict[str, dict[str, object]]:
        """Return module statuses together with runtime enablement flags."""
        experimental_enabled = bool(getattr(self._runtime_feature_policy, 'experimental_modules_enabled', False))
        details: dict[str, dict[str, object]] = {}
        for module_id, status in self.snapshot().items():
            enabled = bool(status != 'experimental' or experimental_enabled)
            details[str(module_id)] = {'status': str(status), 'enabled': enabled}
        return details

    def render_markdown(self) -> str:
        """Render the module-status snapshot as deterministic markdown.

        Returns:
            str: Markdown bullet list grouped by status label.

        Raises:
            None: Rendering is a pure formatting operation.
        """
        return render_module_status_markdown(self.snapshot_details())
