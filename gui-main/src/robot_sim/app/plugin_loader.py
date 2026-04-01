from __future__ import annotations

from dataclasses import dataclass, field
import inspect
from importlib import import_module
from importlib.metadata import entry_points
from pathlib import Path
from typing import Callable

import yaml

from robot_sim.application.services.runtime_feature_service import RuntimeFeaturePolicy


@dataclass(frozen=True)
class PluginManifest:
    """Controlled plugin declaration loaded from configuration."""

    plugin_id: str
    kind: str
    factory: str = ''
    entry_point: str = ''
    aliases: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
    source: str = 'external'
    replace: bool = False
    enabled_profiles: tuple[str, ...] = ()
    status: str = 'experimental'

    def allows_profile(self, profile: str) -> bool:
        """Return whether the plugin is enabled for the supplied profile."""
        if not self.enabled_profiles:
            return True
        return str(profile) in set(self.enabled_profiles)


@dataclass(frozen=True)
class PluginRegistration:
    """Resolved plugin payload ready for a registry."""

    plugin_id: str
    instance: object
    aliases: tuple[str, ...]
    metadata: dict[str, object]
    replace: bool = False
    source: str = 'external'


class PluginLoader:
    """Load externally declared plugins under a strict allowlist."""

    def __init__(self, config_path: str | Path, *, policy: RuntimeFeaturePolicy) -> None:
        self._config_path = Path(config_path)
        self._policy = policy

    def manifests(self, kind: str) -> tuple[PluginManifest, ...]:
        """Return validated manifests of the requested plugin kind."""
        if not self._policy.plugin_discovery_enabled or not self._config_path.exists():
            return ()
        payload = yaml.safe_load(self._config_path.read_text(encoding='utf-8')) or {}
        if not isinstance(payload, dict):
            raise ValueError(f'plugin manifest must be a mapping: {self._config_path}')
        raw_plugins = payload.get('plugins', ())
        if raw_plugins is None:
            return ()
        if not isinstance(raw_plugins, list):
            raise ValueError(f'plugins section must be a list: {self._config_path}')
        manifests: list[PluginManifest] = []
        for entry in raw_plugins:
            if not isinstance(entry, dict):
                raise ValueError(f'plugin entry must be a mapping: {self._config_path}')
            factory = str(entry.get('factory', '') or '')
            entry_point_ref = str(entry.get('entry_point', '') or '')
            if not factory and not entry_point_ref:
                raise ValueError(f'plugin entry must define factory or entry_point: {self._config_path}')
            manifest = PluginManifest(
                plugin_id=str(entry['id']),
                kind=str(entry['kind']),
                factory=factory,
                entry_point=entry_point_ref,
                aliases=tuple(str(alias) for alias in entry.get('aliases', ()) or ()),
                metadata=dict(entry.get('metadata', {}) or {}),
                source=str(entry.get('source', 'entry_point' if entry_point_ref else 'external')),
                replace=bool(entry.get('replace', False)),
                enabled_profiles=tuple(str(profile) for profile in entry.get('enabled_profiles', ()) or ()),
                status=str(entry.get('status', 'experimental')),
            )
            if manifest.kind != str(kind):
                continue
            if not manifest.allows_profile(self._policy.active_profile):
                continue
            manifests.append(manifest)
        return tuple(manifests)

    def registrations(self, kind: str, **context) -> tuple[PluginRegistration, ...]:
        """Resolve manifests into callable registry payloads."""
        registrations: list[PluginRegistration] = []
        for manifest in self.manifests(kind):
            factory = self._resolve_factory(manifest)
            payload = self._call_factory(factory, context)
            instance = payload['instance'] if isinstance(payload, dict) else payload
            metadata = dict(manifest.metadata)
            aliases = manifest.aliases
            if isinstance(payload, dict):
                metadata.update(dict(payload.get('metadata', {}) or {}))
                aliases = tuple(str(alias) for alias in payload.get('aliases', aliases) or ())
            metadata.setdefault('status', manifest.status)
            metadata.setdefault('source', manifest.source)
            registrations.append(
                PluginRegistration(
                    plugin_id=manifest.plugin_id,
                    instance=instance,
                    aliases=aliases,
                    metadata=metadata,
                    replace=manifest.replace,
                    source=manifest.source,
                )
            )
        return tuple(registrations)

    def _resolve_factory(self, manifest: PluginManifest) -> Callable[..., object]:
        if manifest.entry_point:
            return self._resolve_entry_point(manifest.entry_point)
        module_name, _, attr_name = str(manifest.factory).partition(':')
        if not module_name or not attr_name:
            raise ValueError(f'invalid plugin factory path: {manifest.factory}')
        module = import_module(module_name)
        factory = getattr(module, attr_name)
        if not callable(factory):
            raise TypeError(f'plugin factory is not callable: {manifest.factory}')
        return factory

    @staticmethod
    def _resolve_entry_point(entry_point_ref: str) -> Callable[..., object]:
        group, _, name = str(entry_point_ref).partition(':')
        if not group or not name:
            raise ValueError(f'invalid plugin entry_point reference: {entry_point_ref}')
        discovered = entry_points()
        if hasattr(discovered, 'select'):
            matches = tuple(discovered.select(group=group, name=name))
        else:  # pragma: no cover - compatibility fallback
            matches = tuple(ep for ep in discovered.get(group, ()) if ep.name == name)
        if not matches:
            raise ValueError(f'plugin entry point not found: {entry_point_ref}')
        payload = matches[0].load()
        if callable(payload):
            return payload
        return lambda **_context: payload

    @staticmethod
    def _call_factory(factory: Callable[..., object], context: dict[str, object]) -> object:
        """Call a plugin factory without conflating signature mismatch and factory failure.

        Args:
            factory: Resolved factory callable.
            context: Keyword context assembled by the composition root.

        Returns:
            object: Factory return payload.

        Raises:
            TypeError: Propagates factory-internal ``TypeError`` failures unchanged.
            ValueError: Raised when the factory signature cannot accept the supported calling modes.

        Boundary behavior:
            Signature compatibility is resolved before execution. The factory is invoked exactly once,
            either with the supplied context or without arguments.
        """
        signature = inspect.signature(factory)
        parameters = tuple(signature.parameters.values())
        accepts_var_kw = any(param.kind is inspect.Parameter.VAR_KEYWORD for param in parameters)
        required_keyword_only = [
            param.name
            for param in parameters
            if param.kind is inspect.Parameter.KEYWORD_ONLY and param.default is inspect._empty
        ]
        accepts_named_context = all(name in signature.parameters or accepts_var_kw for name in context)
        if accepts_named_context:
            return factory(**context)
        required_without_defaults = [
            param.name
            for param in parameters
            if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            and param.default is inspect._empty
        ]
        if not required_without_defaults and not required_keyword_only:
            return factory()
        raise ValueError(
            f'plugin factory signature incompatible with supported calling modes: {factory!r}; '
            f'required_positional={required_without_defaults}; required_keyword_only={required_keyword_only}'
        )
