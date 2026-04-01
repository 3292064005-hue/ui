from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from robot_sim.application.services.config_service import ConfigService


@dataclass(frozen=True)
class RuntimeFeaturePolicy:
    """Profile-scoped runtime feature toggles.

    Attributes:
        active_profile: Active configuration profile.
        experimental_modules_enabled: Whether experimental modules may be mounted/used.
        experimental_backends_enabled: Whether experimental backends may be advertised as available.
        plugin_discovery_enabled: Whether externally declared plugins may be discovered and loaded.
        contract_doc_autogen_enabled: Whether CI/profile expects contract docs to be regenerated.
    """

    active_profile: str = ConfigService.DEFAULT_PROFILE
    experimental_modules_enabled: bool = False
    experimental_backends_enabled: bool = False
    plugin_discovery_enabled: bool = False
    contract_doc_autogen_enabled: bool = False

    def as_dict(self) -> dict[str, object]:
        """Return the policy as a serializable mapping."""
        return {
            'active_profile': self.active_profile,
            'experimental_modules_enabled': self.experimental_modules_enabled,
            'experimental_backends_enabled': self.experimental_backends_enabled,
            'plugin_discovery_enabled': self.plugin_discovery_enabled,
            'contract_doc_autogen_enabled': self.contract_doc_autogen_enabled,
        }


class RuntimeFeatureService:
    """Resolve runtime feature toggles from profile overlays."""

    DEFAULT_FEATURES: dict[str, bool] = {
        'experimental_modules_enabled': False,
        'experimental_backends_enabled': False,
        'plugin_discovery_enabled': False,
        'contract_doc_autogen_enabled': False,
    }

    def __init__(self, config_service: ConfigService) -> None:
        self._config_service = config_service

    def load_policy(self) -> RuntimeFeaturePolicy:
        """Load the active runtime feature policy.

        Returns:
            RuntimeFeaturePolicy: Feature toggles merged from default and active profile overlays.

        Raises:
            ValueError: If a profile defines a non-mapping ``features`` section.
        """
        merged = dict(self.DEFAULT_FEATURES)
        for profile_name in (ConfigService.DEFAULT_PROFILE, self._config_service.profile):
            overlay = self._features_overlay(profile_name)
            if overlay:
                merged.update(overlay)
        return RuntimeFeaturePolicy(
            active_profile=self._config_service.profile,
            experimental_modules_enabled=bool(merged['experimental_modules_enabled']),
            experimental_backends_enabled=bool(merged['experimental_backends_enabled']),
            plugin_discovery_enabled=bool(merged['plugin_discovery_enabled']),
            contract_doc_autogen_enabled=bool(merged['contract_doc_autogen_enabled']),
        )

    def _features_overlay(self, profile_name: str) -> dict[str, bool]:
        payload = self._config_service.load_profile_yaml(profile_name)
        if not payload:
            return {}
        features = payload.get('features', {})
        if features is None:
            return {}
        if not isinstance(features, Mapping):
            raise ValueError(f'profile features must be a mapping: {profile_name}')
        normalized: dict[str, bool] = {}
        for key, default_value in self.DEFAULT_FEATURES.items():
            if key in features:
                normalized[key] = bool(features[key])
            else:
                normalized[key] = bool(default_value)
        return normalized
