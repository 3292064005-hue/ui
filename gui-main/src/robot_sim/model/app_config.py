from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class WindowConfig:
    """Typed UI window configuration."""

    title: str = 'Robot Sim Engine'
    width: int = 1680
    height: int = 980
    splitter_sizes: tuple[int, ...] = (420, 820, 360)
    vertical_splitter_sizes: tuple[int, ...] = (700, 260)

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload['splitter_sizes'] = list(self.splitter_sizes)
        payload['vertical_splitter_sizes'] = list(self.vertical_splitter_sizes)
        return payload


@dataclass(frozen=True)
class PlotConfig:
    """Typed plotting configuration."""

    max_points: int = 5000

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class AppConfig:
    """Typed application configuration grouping high-frequency UI settings."""

    window: WindowConfig = field(default_factory=WindowConfig)
    plots: PlotConfig = field(default_factory=PlotConfig)

    def as_dict(self) -> dict[str, object]:
        return {
            'window': self.window.as_dict(),
            'plots': self.plots.as_dict(),
        }
