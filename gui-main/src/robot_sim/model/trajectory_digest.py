from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np


_ARRAY_METADATA_KEYS = (
    ('q', 'joint_state_digest'),
    ('joint_positions', 'joint_positions_digest'),
    ('ee_positions', 'ee_positions_digest'),
    ('ee_rotations', 'ee_rotations_digest'),
    ('t', 'time_digest'),
)


def array_digest(array: object) -> dict[str, object]:
    """Return a deterministic digest payload for a numeric array.

    Args:
        array: Array-like object to normalize and hash.

    Returns:
        dict[str, object]: Shape, dtype, and content hash for the array.

    Raises:
        None: Invalid inputs are coerced via ``numpy.asarray``.
    """
    normalized = np.ascontiguousarray(np.asarray(array, dtype=float))
    return {
        'shape': tuple(int(v) for v in normalized.shape),
        'dtype': str(normalized.dtype),
        'sha1': hashlib.sha1(normalized.tobytes()).hexdigest(),
    }



def trajectory_digest_payload(trajectory: Any) -> dict[str, object]:
    """Build a deterministic digest payload for a trajectory-like object.

    Args:
        trajectory: Trajectory-like object exposing ``t``/``q`` and optional FK caches.

    Returns:
        dict[str, object]: Canonical digest payload suitable for hashing and diagnostics.

    Raises:
        None: Missing optional arrays are represented as ``None``.
    """
    payload: dict[str, object] = {}
    for attr_name, _ in _ARRAY_METADATA_KEYS:
        value = getattr(trajectory, attr_name, None)
        payload[attr_name] = None if value is None else array_digest(value)
    return payload



def compute_trajectory_digest(trajectory: Any) -> str:
    """Compute a stable SHA-1 digest for a trajectory-like object.

    Args:
        trajectory: Trajectory-like object exposing numeric arrays.

    Returns:
        str: Stable digest string.

    Raises:
        None: This helper is a pure deterministic projection.
    """
    payload = trajectory_digest_payload(trajectory)
    return hashlib.sha1(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()



def ensure_trajectory_digest_metadata(trajectory: Any) -> str:
    """Ensure a trajectory metadata dictionary contains deterministic digest fields.

    Args:
        trajectory: Trajectory-like object exposing a mutable ``metadata`` mapping.

    Returns:
        str: Canonical trajectory digest.

    Raises:
        None: Missing metadata mappings are treated as absent.
    """
    metadata = getattr(trajectory, 'metadata', None)
    if not isinstance(metadata, dict):
        return compute_trajectory_digest(trajectory)
    existing = str(metadata.get('trajectory_digest', '') or '').strip()
    if existing:
        return existing
    payload = trajectory_digest_payload(trajectory)
    digest = hashlib.sha1(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()
    metadata['trajectory_digest'] = digest
    for attr_name, metadata_key in _ARRAY_METADATA_KEYS:
        if payload.get(attr_name) is not None:
            metadata[metadata_key] = payload[attr_name]
    return digest
