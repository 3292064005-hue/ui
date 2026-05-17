#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.training.exporters.model_export_service import ModelExportService
from spine_ultrasound_ui.training.specs.frame_anatomy_keypoint_training_spec import FrameAnatomyKeypointTrainingSpec
from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.specs.uca_training_spec import UCATrainingSpec
from spine_ultrasound_ui.training.trainers.frame_anatomy_keypoint_trainer import FrameAnatomyKeypointTrainer
from spine_ultrasound_ui.training.trainers.lamina_keypoint_trainer import LaminaKeypointTrainer
from spine_ultrasound_ui.training.trainers.lamina_seg_trainer import LaminaSegTrainer
from spine_ultrasound_ui.training.trainers.uca_slice_rank_trainer import UCASliceRankTrainer
from spine_ultrasound_ui.utils import ensure_dir, now_text


TASKS = ('frame_anatomy_keypoint', 'lamina_seg', 'lamina_keypoint', 'uca_rank')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Run fixture-backed model training/export or emit backend training requests.')
    parser.add_argument('--task', choices=TASKS + ('all',), default='all')
    parser.add_argument('--backend', choices=('numpy_baseline', 'monai', 'nnunetv2'), default='numpy_baseline')
    parser.add_argument('--config', default='', help='Optional task-specific training config file')
    parser.add_argument('--output-root', default='training_outputs/model_pipeline')
    parser.add_argument('--promote-to', default='', help='Optional model root that receives exported runtime packages')
    parser.add_argument('--runtime-config-dir', default='', help='Optional runtime config directory to update for exported packages')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = ensure_dir(Path(args.output_root))
    tasks = list(TASKS) if args.task == 'all' else [args.task]
    fixture_root = ensure_dir(output_root / 'fixtures')
    package_root = ensure_dir(output_root / 'packages')
    request_root = ensure_dir(output_root / 'requests')
    promote_root = Path(args.promote_to) if args.promote_to else None
    if promote_root is not None:
        promote_root = ensure_dir(promote_root)
    promotes_repo_models = promote_root is not None and promote_root.resolve() == (ROOT / 'models').resolve()
    runtime_config_dir = Path(args.runtime_config_dir) if args.runtime_config_dir else (ROOT / 'configs' / 'models' if promotes_repo_models else output_root / 'runtime_configs')
    runtime_config_dir = ensure_dir(runtime_config_dir)

    results = []
    for task in tasks:
        try:
            result = run_task(task, args.backend, fixture_root, package_root, request_root, Path(args.config) if args.config else None)
            if result.get('package_dir') and promote_root is not None:
                promoted = promote_package(Path(result['package_dir']), promote_root)
                result['promoted_package_dir'] = str(promoted)
                write_runtime_config(task, promoted, runtime_config_dir)
            elif result.get('package_dir'):
                write_runtime_config(task, Path(result['package_dir']), runtime_config_dir)
            results.append({'task': task, 'ok': True, **result})
        except Exception as exc:
            results.append({'task': task, 'ok': False, 'error': f'{type(exc).__name__}:{exc}'})
            if args.backend == 'numpy_baseline':
                raise

    summary = {
        'generated_at': now_text(),
        'backend': args.backend,
        'task': args.task,
        'output_root': str(output_root),
        'results': results,
    }
    summary_path = output_root / f'model_training_pipeline_{args.backend}_{args.task}.json'
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'summary_path': str(summary_path), 'ok': all(item.get('ok') for item in results)}, ensure_ascii=False))
    return 0 if all(item.get('ok') for item in results) else 2


def run_task(task: str, backend: str, fixture_root: Path, package_root: Path, request_root: Path, config_path: Path | None) -> dict[str, Any]:
    if task == 'frame_anatomy_keypoint':
        if backend != 'numpy_baseline':
            return backend_placeholder(task, backend, request_root, 'frame anatomy training currently exports numpy template packages only')
        spec = FrameAnatomyKeypointTrainingSpec.from_file(config_path) if config_path else FrameAnatomyKeypointTrainingSpec.from_file(ROOT / 'configs' / 'training' / 'frame_anatomy_keypoint_training.yaml')
        trainer = FrameAnatomyKeypointTrainer()
        training_result = trainer.train(spec)
        export = trainer.export_runtime_package(training_result, spec, package_dir=package_root / 'frame_anatomy_keypoint')
        return {'mode': 'exported_package', **export}

    if task in {'lamina_seg', 'lamina_keypoint'}:
        lamina_root = ensure_lamina_fixture(fixture_root / 'lamina_center')
        spec = LaminaCenterTrainingSpec.from_file(config_path) if config_path else LaminaCenterTrainingSpec(
            dataset_root=lamina_root,
            split_file=lamina_root / 'splits' / 'split_v1.json',
            output_dir=request_root / 'lamina_center',
            trainer_backend=backend,
        )
        spec.trainer_backend = backend
        if task == 'lamina_seg':
            result = LaminaSegTrainer().train(spec)
            if backend == 'numpy_baseline':
                package = ModelExportService().export_segmentation_model(result, package_root)
                return {'mode': 'exported_package', **package}
            return {'mode': 'backend_request', 'training_request_path': str(result.get('training_request_path', '')), 'dependency_status': result.get('dependency_status', {}), 'launch_plan': result.get('launch_plan', {})}
        if backend == 'nnunetv2':
            return backend_placeholder(task, backend, request_root, 'nnU-Net keypoint package export is not implemented; use MONAI request or numpy baseline')
        result = LaminaKeypointTrainer().train(spec)
        if backend == 'numpy_baseline':
            package = ModelExportService().export_keypoint_model(result, package_root)
            return {'mode': 'exported_package', **package}
        return {'mode': 'backend_request', 'training_request_path': str(result.get('training_request_path', '')), 'dependency_status': result.get('dependency_status', {}), 'launch_plan': result.get('launch_plan', {})}

    if task == 'uca_rank':
        uca_root = ensure_uca_fixture(fixture_root / 'uca')
        spec = UCATrainingSpec.from_file(config_path) if config_path else UCATrainingSpec(
            dataset_root=uca_root,
            split_file=uca_root / 'splits' / 'split_v1.json',
            output_dir=request_root / 'uca',
            trainer_backend=backend,
        )
        spec.trainer_backend = backend
        if backend == 'nnunetv2':
            return backend_placeholder(task, backend, request_root, 'nnU-Net UCA support is dataset-export only; ranking request uses MONAI or numpy baseline')
        result = UCASliceRankTrainer().train(spec)
        if backend == 'numpy_baseline':
            package = ModelExportService().export_ranking_model(result, package_root)
            return {'mode': 'exported_package', **package}
        return {'mode': 'backend_request', 'training_request_path': str(result.get('training_request_path', '')), 'dependency_status': result.get('dependency_status', {}), 'launch_plan': result.get('launch_plan', {})}

    raise ValueError(f'unsupported task: {task}')


def ensure_lamina_fixture(root: Path) -> Path:
    case_dir = ensure_dir(root / 'raw_cases' / 'fixture001' / 'session001')
    image = np.linspace(0.0, 1.0, 64, dtype=np.float32).reshape(8, 8)
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    np.savez_compressed(case_dir / 'bone_mask.npz', mask=(image > 0.6).astype(np.float32))
    write_json(case_dir / 'meta.json', {'patient_id': 'fixture001', 'session_id': 'session001', 'dataset_role': 'lamina_center'})
    write_json(root / 'annotations' / 'lamina_centers' / 'fixture001__session001.json', {
        'schema_version': '1.0',
        'case_id': 'fixture001/session001',
        'patient_id': 'fixture001',
        'session_id': 'session001',
        'coordinate_frame': 'coronal_vpi_mm',
        'points': [
            {'point_id': 'p1', 'vertebra_instance_id': 'v1', 'side': 'left', 'x_mm': -40.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
            {'point_id': 'p2', 'vertebra_instance_id': 'v1', 'side': 'right', 'x_mm': 40.0, 'y_mm': 20.0, 'z_mm': 0.0, 'visibility': 'clear'},
        ],
    })
    write_json(root / 'annotations' / 'vertebra_pairs' / 'fixture001__session001.json', {
        'schema_version': '1.0',
        'case_id': 'fixture001/session001',
        'pairs': [{'vertebra_instance_id': 'v1', 'left_point_id': 'p1', 'right_point_id': 'p2', 'pair_confidence': 0.9}],
    })
    write_json(root / 'splits' / 'split_v1.json', {'train': ['fixture001/session001'], 'val': [], 'test': []})
    return root


def ensure_uca_fixture(root: Path) -> Path:
    case_dir = ensure_dir(root / 'raw_cases' / 'fixture002' / 'session002')
    image = np.tile(np.linspace(0.1, 0.9, 16, dtype=np.float32), (12, 1))
    np.savez_compressed(case_dir / 'coronal_vpi.npz', image=image)
    write_json(case_dir / 'meta.json', {'patient_id': 'fixture002', 'session_id': 'session002', 'dataset_role': 'uca'})
    write_json(root / 'annotations' / 'uca_labels' / 'fixture002__session002.json', {'schema_version': '1.0', 'case_id': 'fixture002/session002', 'best_slice_index': 5, 'uca_angle_deg': 18.2})
    write_json(root / 'annotations' / 'slice_ranking' / 'fixture002__session002.json', {'ranked_slices': [{'slice_index': 5, 'score': 0.9}, {'slice_index': 4, 'score': 0.8}], 'best_slice': {'slice_index': 5, 'score': 0.9}})
    ensure_dir(root / 'annotations' / 'bone_feature_masks')
    np.savez_compressed(root / 'annotations' / 'bone_feature_masks' / 'fixture002__session002.npz', mask=(image > 0.5).astype(np.float32))
    write_json(root / 'splits' / 'split_v1.json', {'train': ['fixture002/session002'], 'val': [], 'test': []})
    return root


def backend_placeholder(task: str, backend: str, request_root: Path, reason: str) -> dict[str, Any]:
    path = ensure_dir(request_root / backend) / f'{task}_{backend}_unsupported_request.json'
    payload = {'generated_at': now_text(), 'task_name': task, 'trainer_backend': backend, 'mode': 'backend_request_placeholder', 'status': 'unsupported_backend_for_task', 'reason': reason}
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
    return {'mode': 'backend_request', 'status': 'unsupported_backend_for_task', 'training_request_path': str(path), 'dependency_status': {'available': False, 'missing_modules': []}, 'launch_plan': {}}


def promote_package(package_dir: Path, promote_root: Path) -> Path:
    target = promote_root / package_dir.name
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(package_dir, target)
    return target


def write_runtime_config(task: str, package_dir: Path, runtime_config_dir: Path) -> None:
    config_name = {
        'frame_anatomy_keypoint': 'frame_anatomy_keypoint_runtime.yaml',
        'lamina_seg': 'lamina_seg_runtime.yaml',
        'lamina_keypoint': 'lamina_keypoint_runtime.yaml',
        'uca_rank': 'uca_rank_runtime.yaml',
    }[task]
    meta = json.loads((package_dir / 'model_meta.json').read_text(encoding='utf-8'))
    rel_package = relative_or_absolute(package_dir, runtime_config_dir)
    lines = [f'package_dir: {rel_package}', f"backend: {meta.get('backend', meta.get('trainer_backend', 'numpy_baseline'))}", 'strict_runtime_required: true']
    runtime_model_path = str(meta.get('runtime_model_path', '') or '')
    if runtime_model_path:
        lines.append(f'runtime_model_path: {relative_or_absolute(package_dir / runtime_model_path, runtime_config_dir)}')
    benchmark_manifest = str(meta.get('benchmark_manifest_path', '') or '')
    if benchmark_manifest:
        lines.append(f'benchmark_manifest: {relative_or_absolute(package_dir / benchmark_manifest, runtime_config_dir)}')
        lines.append(f"required_release_state: {meta.get('release_state', '')}")
        lines.append('require_benchmark_gate: true')
    (runtime_config_dir / config_name).write_text('\n'.join(lines) + '\n', encoding='utf-8')


def relative_or_absolute(path: Path, base: Path) -> str:
    try:
        import os
        return os.path.relpath(path.resolve(), start=base.resolve())
    except Exception:
        try:
            return str(path.resolve().relative_to(ROOT))
        except Exception:
            return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
