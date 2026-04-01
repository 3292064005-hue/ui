from __future__ import annotations


class PlotSync:
    def __init__(self) -> None:
        self._last_x = 0.0

    @property
    def last_x(self) -> float:
        return float(self._last_x)

    def sync(self, plots_manager, plot_keys: list[str], x_value: float) -> None:
        self._last_x = float(x_value)
        for key in plot_keys:
            plots_manager.set_cursor(key, self._last_x)
