#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATH_KEYS = {'weights_path', 'entrypoint', 'parameter_path', 'meta_path', 'benchmark_manifest_path', 'runtime_model_path', 'package_dir', 'dataset_manifest', 'output_dir'}


def _is_absolute_or_machine_path(value: str) -> bool:
    return value.startswith('/tmp/') or value.startswith('/mnt/data/') or value.startswith('/home/') or (len(value) > 2 and value[1] == ':' and value[2] in ('\\', '/'))


def _scan_portable_paths(path: Path, payload: object) -> str:
    stack = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key in PATH_KEYS and isinstance(value, str) and _is_absolute_or_machine_path(value):
                    return f'{path}: non-portable {key}={value}'
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(current, list):
            stack.extend(item for item in current if isinstance(item, (dict, list)))
    return ''


def main() -> int:
    manifests = list(ROOT.glob('models/*/bundle_manifest.json'))
    if not manifests:
        print('[FAIL] no model bundle manifests found', file=sys.stderr)
        return 1
    required = {
        'bundle_id',
        'bundle_version',
        'runtime_profile',
        'artifacts',
        'compatibility',
        'metrics',
        'training_run_id',
        'dataset_source',
        'dataset_hash',
        'trainer_backend',
        'release_state',
        'clinical_claim',
        'strict_runtime_required',
    }
    for path in manifests:
        payload = json.loads(path.read_text(encoding='utf-8'))
        portable_error = _scan_portable_paths(path, payload)
        if portable_error:
            print(f'[FAIL] {portable_error}', file=sys.stderr)
            return 1
        missing = sorted(required - payload.keys())
        if missing:
            print(f'[FAIL] {path}: missing {missing}', file=sys.stderr)
            return 1
        artifacts = payload.get('artifacts', {})
        for key in ('weights_path', 'entrypoint', 'parameter_path', 'meta_path'):
            if not artifacts.get(key):
                print(f'[FAIL] {path}: artifacts.{key} missing', file=sys.stderr)
                return 1
        package_dir = path.parent
        for artifact_key in ('weights_path', 'parameter_path', 'meta_path'):
            artifact_path = package_dir / str(artifacts.get(artifact_key, ''))
            if not artifact_path.exists():
                print(f'[FAIL] {path}: artifacts.{artifact_key} target missing: {artifact_path}', file=sys.stderr)
                return 1
        meta_path = package_dir / str(artifacts.get('meta_path'))
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        portable_error = _scan_portable_paths(meta_path, meta)
        if portable_error:
            print(f'[FAIL] {portable_error}', file=sys.stderr)
            return 1
        for meta_key in ('training_run_id', 'dataset_source', 'dataset_hash', 'trainer_backend', 'release_state', 'clinical_claim', 'strict_runtime_required'):
            if meta_key not in meta:
                print(f'[FAIL] {meta_path}: missing {meta_key}', file=sys.stderr)
                return 1
        benchmark_ref = str(payload.get('benchmark_manifest_path', '') or meta.get('benchmark_manifest_path', '') or '')
        if benchmark_ref and not (package_dir / benchmark_ref).exists():
            print(f'[FAIL] {path}: benchmark manifest missing: {benchmark_ref}', file=sys.stderr)
            return 1
    print(f'[OK] validated {len(manifests)} model bundle manifests')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
