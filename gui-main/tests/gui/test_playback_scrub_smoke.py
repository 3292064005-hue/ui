from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from robot_sim.presentation.widgets.playback_panel import PlaybackPanel


def test_playback_panel_scrub_updates_slider_and_label():
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    panel = PlaybackPanel()
    panel.set_total_frames(10)
    panel.set_frame(4, 10)
    assert panel.slider.value() == 4
    assert panel.cursor_label.text() == "4 / 9"
    panel.close()
