from __future__ import annotations


class SubmissionPolicyEngine:
    """Resolve how a new start request should behave while a task is active."""

    def __init__(self, mode: str) -> None:
        """Store the orchestration submission mode.

        Args:
            mode: Policy name such as ``cancel_and_replace`` or ``queue_latest``.

        Returns:
            None: Construction stores policy configuration only.

        Raises:
            None: Construction is side-effect free.
        """
        self.mode = str(mode)

    def decide(self, *, is_running: bool) -> str:
        """Return the action for an incoming start request.

        Args:
            is_running: Whether an orchestrated task is currently active.

        Returns:
            str: One of ``start_now``, ``reject``, ``queue_latest`` or ``cancel_and_replace``.

        Raises:
            None: Pure policy lookup.
        """
        if not is_running:
            return 'start_now'
        if self.mode == 'reject_if_running':
            return 'reject'
        if self.mode == 'queue_latest':
            return 'queue_latest'
        return 'cancel_and_replace'
