from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from robot_sim.infra.schema import ConfigSchema
from robot_sim.model.app_config import AppConfig, PlotConfig, WindowConfig
from robot_sim.model.solver_config import IKConfig, SolverSettings, TrajectoryConfig


class ConfigService:
    """Load application and solver configuration with profile-aware overrides.

    Resolution order is deliberately explicit so release, CI, GUI, and local development
    can share a common baseline without duplicating the full configuration tree.
    """

    DEFAULT_PROFILE = 'default'
    PROFILE_DIR_NAME = 'profiles'
    DEFAULT_APP_CONFIG: dict[str, object] = {
        'window': {
            'title': 'Robot Sim Engine',
            'width': 1680,
            'height': 980,
            'splitter_sizes': [420, 820, 360],
            'vertical_splitter_sizes': [700, 260],
        },
        'plots': {
            'max_points': 5000,
        },
    }
    DEFAULT_SOLVER_CONFIG: dict[str, object] = {
        'ik': {
            'mode': 'dls',
            'max_iters': 150,
            'pos_tol': 1.0e-4,
            'ori_tol': 1.0e-4,
            'damping_lambda': 0.05,
            'step_scale': 0.5,
            'enable_nullspace': True,
            'joint_limit_weight': 0.03,
            'manipulability_weight': 0.0,
            'position_only': False,
            'orientation_weight': 1.0,
            'max_step_norm': 0.35,
            'fallback_to_dls_when_singular': True,
            'reachability_precheck': True,
            'retry_count': 1,
            'random_seed': 7,
            'adaptive_damping': True,
            'min_damping_lambda': 1.0e-4,
            'max_damping_lambda': 1.5,
            'use_weighted_least_squares': True,
            'clamp_seed_to_joint_limits': True,
            'normalize_target_rotation': True,
            'allow_orientation_relaxation': False,
            'orientation_relaxation_pos_multiplier': 5.0,
            'orientation_relaxation_ori_multiplier': 25.0,
        },
        'trajectory': {
            'duration': 3.0,
            'dt': 0.02,
        },
    }

    def __init__(self, config_dir: str | Path, *, profile: str = DEFAULT_PROFILE) -> None:
        """Create the config service.

        Args:
            config_dir: Directory containing ``app.yaml``, ``solver.yaml``, and optional
                ``profiles/<profile>.yaml`` overlays.
            profile: Active configuration profile. ``default`` uses only the shared
                baseline unless a local override file exists.

        Returns:
            None: Stores configuration paths and profile state.

        Raises:
            ValueError: If ``profile`` is empty.
        """
        normalized_profile = str(profile or '').strip()
        if not normalized_profile:
            raise ValueError('ConfigService profile must be a non-empty string')
        self.config_dir = Path(config_dir)
        self.profile = normalized_profile

    @property
    def profile_dir(self) -> Path:
        """Return the profile-directory path."""
        return self.config_dir / self.PROFILE_DIR_NAME

    def available_profiles(self) -> tuple[str, ...]:
        """Return the available configuration profile identifiers.

        Returns:
            tuple[str, ...]: Sorted profile identifiers discovered on disk.

        Raises:
            None: Missing profile directories simply yield an empty tuple.
        """
        if not self.profile_dir.exists():
            return ()
        return tuple(sorted(path.stem for path in self.profile_dir.glob('*.yaml') if path.is_file()))

    def load_yaml(self, name: str) -> dict:
        """Load a YAML mapping from the config directory.

        Args:
            name: Relative YAML filename under ``config_dir``.

        Returns:
            dict: Parsed mapping or an empty mapping when the file is absent.

        Raises:
            ValueError: If the YAML payload is not a mapping.
        """
        path = self.config_dir / name
        if not path.exists():
            return {}
        with path.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f'config must be a mapping: {path}')
        return data

    def load_profile_yaml(self, profile: str | None = None) -> dict:
        """Load a profile overlay mapping.

        Args:
            profile: Optional explicit profile name. Defaults to the active profile.

        Returns:
            dict: Profile mapping or an empty mapping when no overlay is defined.

        Raises:
            ValueError: If the profile YAML payload is not a mapping.
        """
        resolved_profile = str(profile or self.profile).strip()
        if resolved_profile == self.DEFAULT_PROFILE:
            profile_path = self.profile_dir / f'{self.DEFAULT_PROFILE}.yaml'
        else:
            profile_path = self.profile_dir / f'{resolved_profile}.yaml'
        if not profile_path.exists():
            return {}
        with profile_path.open('r', encoding='utf-8') as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f'profile config must be a mapping: {profile_path}')
        return data

    def load_app_config(self) -> dict[str, object]:
        """Load the validated application UI configuration as a plain mapping."""
        merged = self._merge_profile_section(self.DEFAULT_APP_CONFIG, section_keys=('window', 'plots'), local_name='app.yaml')
        return ConfigSchema.validate_app_config(merged)

    def load_solver_config(self) -> dict[str, object]:
        """Load the validated solver and trajectory configuration as a plain mapping."""
        raw = self._merge_profile_section(self.DEFAULT_SOLVER_CONFIG, section_keys=('ik', 'trajectory'), local_name='solver.yaml')
        normalized = deepcopy(raw)
        ik = normalized.setdefault('ik', {})
        if 'damping_lambda' not in ik and 'damping' in ik:
            ik['damping_lambda'] = ik['damping']
        return ConfigSchema.validate_solver_config(normalized)

    def load_app_settings(self) -> AppConfig:
        """Load the application configuration as typed settings objects.

        Returns:
            AppConfig: Typed application configuration.

        Raises:
            SchemaError: If the underlying app configuration is invalid.
        """
        config = self.load_app_config()
        window = dict(config.get('window', {}) or {})
        plots = dict(config.get('plots', {}) or {})
        return AppConfig(
            window=WindowConfig(
                title=str(window.get('title', WindowConfig.title)),
                width=int(window.get('width', WindowConfig.width)),
                height=int(window.get('height', WindowConfig.height)),
                splitter_sizes=tuple(int(v) for v in window.get('splitter_sizes', WindowConfig.splitter_sizes) or WindowConfig.splitter_sizes),
                vertical_splitter_sizes=tuple(int(v) for v in window.get('vertical_splitter_sizes', WindowConfig.vertical_splitter_sizes) or WindowConfig.vertical_splitter_sizes),
            ),
            plots=PlotConfig(
                max_points=int(plots.get('max_points', PlotConfig.max_points)),
            ),
        )

    def load_solver_settings(self) -> SolverSettings:
        """Load the solver configuration as typed settings objects.

        Returns:
            SolverSettings: Typed solver and trajectory configuration bundle.

        Raises:
            SchemaError: If the underlying solver configuration is invalid.
        """
        config = self.load_solver_config()
        ik = dict(config.get('ik', {}) or {})
        trajectory = dict(config.get('trajectory', {}) or {})
        return SolverSettings(
            ik=IKConfig(**ik),
            trajectory=TrajectoryConfig(
                duration=float(trajectory.get('duration', TrajectoryConfig.duration)),
                dt=float(trajectory.get('dt', TrajectoryConfig.dt)),
            ),
        )

    def _merge_profile_section(self, base: dict[str, object], *, section_keys: tuple[str, ...], local_name: str) -> dict[str, object]:
        """Merge baseline, profile, and local overrides for a logical config section.

        Args:
            base: Shared in-code defaults.
            section_keys: Top-level keys owned by the logical section.
            local_name: Local override filename under ``config_dir``.

        Returns:
            dict[str, object]: Deep-merged configuration mapping.

        Raises:
            ValueError: Propagates malformed YAML mapping errors from profile or local files.
        """
        merged = deepcopy(base)
        default_overlay = self._filtered_profile_overlay(self.DEFAULT_PROFILE, section_keys)
        if default_overlay:
            merged = self._deep_merge(merged, default_overlay)
        if self.profile != self.DEFAULT_PROFILE:
            profile_overlay = self._filtered_profile_overlay(self.profile, section_keys)
            if profile_overlay:
                merged = self._deep_merge(merged, profile_overlay)
        local_override = self.load_yaml(local_name)
        if local_override:
            merged = self._deep_merge(merged, local_override)
        return merged

    def _filtered_profile_overlay(self, profile: str, section_keys: tuple[str, ...]) -> dict[str, object]:
        overlay = self.load_profile_yaml(profile)
        if not overlay:
            return {}
        return {str(key): deepcopy(value) for key, value in overlay.items() if str(key) in section_keys}

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Deep-merge two configuration mappings.

        Args:
            base: Base configuration mapping.
            override: Override configuration mapping.

        Returns:
            dict: Deep-merged mapping.

        Raises:
            None: The merge operation is structural only.
        """
        merged = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged
