from __future__ import annotations

import logging
from collections.abc import Iterable

try:
    import pyqtgraph as pg
except Exception:  # pragma: no cover
    pg = None

logger = logging.getLogger(__name__)


class PlotsManager:  # pragma: no cover - GUI shell
    """Thin adapter around the plotting backend used by the presentation layer."""

    def __init__(self, plot_widgets: dict[str, object] | None = None):
        self.plot_widgets = plot_widgets or {}
        self.curves: dict[tuple[str, str], object] = {}
        self.cursors: dict[str, object] = {}
        self._configure_widgets()

    def _configure_widgets(self) -> None:
        if pg is None:
            return
        for key, widget in self.plot_widgets.items():
            try:
                widget.showGrid(x=True, y=True, alpha=0.2)
                widget.setClipToView(True)
                widget.getPlotItem().setMenuEnabled(False)
                widget.setDownsampling(auto=True, mode='peak')
            except Exception as exc:
                logger.warning('failed to configure plot widget %s: %s', key, exc)

    def clear(self, plot_key: str) -> None:
        if pg is None:
            return
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return
        widget.clear()
        self.curves = {k: v for k, v in self.curves.items() if k[0] != plot_key}
        self.cursors.pop(plot_key, None)
        try:
            widget.addLegend()
        except Exception as exc:
            logger.warning('failed to add legend for plot %s: %s', plot_key, exc)

    def ensure_curve(self, plot_key: str, curve_name: str):
        if pg is None:
            return None
        key = (plot_key, curve_name)
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return None
        if key not in self.curves:
            curve = widget.plot(name=curve_name)
            try:
                curve.setClipToView(True)
                curve.setDownsampling(auto=True, method='peak')
                curve.setSkipFiniteCheck(True)
            except Exception as exc:
                logger.debug('curve performance opts unavailable for %s/%s: %s', plot_key, curve_name, exc)
            self.curves[key] = curve
        return self.curves[key]

    def set_curve(self, plot_key: str, curve_name: str, x, y):
        """Set or replace a single named curve."""
        curve = self.ensure_curve(plot_key, curve_name)
        if curve is not None:
            curve.setData(x=x, y=y, skipFiniteCheck=True)

    def set_curves_batch(self, plot_key: str, curves: Iterable[tuple[str, object, object]], *, clear_first: bool = False) -> None:
        """Set multiple curves on the same plot in one call.

        Args:
            plot_key: Target plot identifier.
            curves: Iterable of ``(curve_name, x, y)`` tuples.
            clear_first: Whether to clear the plot before populating curves.

        Returns:
            None: Updates in-memory curve handles and plot widgets.

        Raises:
            None: Missing plotting backends are tolerated.
        """
        if clear_first:
            self.clear(plot_key)
        for curve_name, x, y in curves:
            self.set_curve(plot_key, curve_name, x, y)

    def set_cursor(self, plot_key: str, x_value: float) -> None:
        if pg is None:
            return
        widget = self.plot_widgets.get(plot_key)
        if widget is None:
            return
        cursor = self.cursors.get(plot_key)
        if cursor is None:
            cursor = pg.InfiniteLine(angle=90, movable=False)
            widget.addItem(cursor)
            self.cursors[plot_key] = cursor
        cursor.setValue(float(x_value))

    def set_cursors_batch(self, cursor_updates: Iterable[tuple[str, float]]) -> None:
        """Update multiple plot cursors in one call.

        Args:
            cursor_updates: Iterable of ``(plot_key, x_value)`` cursor updates.

        Returns:
            None: Updates cursor overlays on the configured plots.

        Raises:
            None: Missing plotting backends are tolerated.
        """
        for plot_key, x_value in cursor_updates:
            self.set_cursor(plot_key, x_value)
