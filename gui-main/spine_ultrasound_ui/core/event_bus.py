"""Compatibility shim for the canonical UI-local signal bus.

New code should import from ``spine_ultrasound_ui.core.ui_local_bus`` to avoid
confusion with the runtime event platform under
``spine_ultrasound_ui.services.runtime_event_platform``.
"""

from spine_ultrasound_ui.core.ui_local_bus import QtSignalBus as EventBus
from spine_ultrasound_ui.core.ui_local_bus import get_qt_signal_bus as get_event_bus
from spine_ultrasound_ui.core.ui_local_bus import qt_bus as ebus
