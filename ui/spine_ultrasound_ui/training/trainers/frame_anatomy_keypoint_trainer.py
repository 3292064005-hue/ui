from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.services.benchmark.frame_anatomy_benchmark_service import FrameAnatomyBenchmarkService
from spine_ultrasound_ui.runtime.model_bundle_contract import build_model_bundle_manifest, write_model_bundle_manifest
from spine_ultrasound_ui.training.datasets.frame_anatomy_point_dataset import FrameAnatomyPointDataset
from spine_ultrasound_ui.training.specs.frame_anatomy_keypoint_training_spec import FrameAnatomyKeypointTrainingSpec
from spine_ultrasound_ui.utils import ensure_dir, now_text


class FrameAnatomyKeypointTrainer:
    """Train an exported-weight package for raw-frame anatomy point inference.

    The trainer learns average point templates directly from annotated raw
    ultrasound frames and emits a standalone ``.npz`` weight file. The exported
    package is therefore consumed by the runtime adapter as a genuine external
    weight artifact rather than inline heuristic parameters.
    """

    def train(self, spec: FrameAnatomyKeypointTrainingSpec) -> dict[str, Any]:
        spec.validate()
        if spec.trainer_backend != 'numpy_baseline':
            raise ValueError(f'frame anatomy trainer does not support backend {spec.trainer_backend!r}')
        dataset = FrameAnatomyPointDataset(spec.dataset_manifest)
        patch_radius = int(spec.patch_radius_px)
        left_patches: list[np.ndarray] = []
        right_patches: list[np.ndarray] = []
        separations: list[float] = []
        confidences: list[float] = []
        for sample in dataset:
            image = np.asarray(sample['image'], dtype=np.float32)
            left_patch = self._extract_patch(image, int(sample['left']['x_px']), int(sample['left']['y_px']), patch_radius)
            right_patch = self._extract_patch(image, int(sample['right']['x_px']), int(sample['right']['y_px']), patch_radius)
            left_patches.append(left_patch)
            right_patches.append(right_patch)
            separations.append(abs(float(sample['right']['x_px']) - float(sample['left']['x_px'])))
            confidences.append(1.0)
        left_template = self._normalize_template(np.mean(np.stack(left_patches, axis=0), axis=0))
        right_template = self._normalize_template(np.mean(np.stack(right_patches, axis=0), axis=0))
        learned = {
            'patch_radius_px': patch_radius,
            'template_shape': list(left_template.shape),
            'min_pair_separation_px': int(max(spec.min_pair_separation_px, round(float(np.mean(separations)) * 0.55))),
            'max_temporal_drift_px': float(spec.max_temporal_drift_px),
            'min_stability_score': float(spec.min_stability_score),
            'min_confidence': float(spec.min_confidence),
            'ncc_score_floor': 0.15,
        }
        metrics = {
            'sample_count': len(dataset),
            'avg_pair_separation_px': round(float(np.mean(separations)), 6),
            'avg_confidence': round(float(np.mean(confidences)), 6),
        }
        dataset_hash = self._dataset_hash(dataset)
        training_run_id = f"frame_anatomy_keypoint:{dataset_hash[:16]}"
        output_dir = ensure_dir(spec.output_dir)
        result_path = output_dir / f'{spec.task_name}_frame_anatomy_training_result.json'
        payload = {
            'generated_at': now_text(),
            'task_name': spec.task_name,
            'trainer_backend': spec.trainer_backend,
            'learned_parameters': learned,
            'metrics': metrics,
            'spec': spec.to_dict(),
            'training_run_id': training_run_id,
            'dataset_source': 'fixture',
            'dataset_hash': dataset_hash,
            'release_state': 'research_fixture',
            'clinical_claim': 'non_clinical_research_only',
            'export_weights': {
                'left_template': left_template.tolist(),
                'right_template': right_template.tolist(),
            },
        }
        result_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return payload

    def export_runtime_package(self, training_result: dict[str, Any], spec: FrameAnatomyKeypointTrainingSpec, *, package_dir: Path) -> dict[str, Any]:
        package_dir = ensure_dir(package_dir)
        runtime_model_filename = str(spec.export_model_filename or 'frame_anatomy_keypoint_weights.npz')
        runtime_model_path = package_dir / runtime_model_filename
        export_weights = dict(training_result.get('export_weights', {}) or {})
        left_template = np.asarray(export_weights.get('left_template', []), dtype=np.float32)
        right_template = np.asarray(export_weights.get('right_template', []), dtype=np.float32)
        if left_template.size == 0 or right_template.size == 0:
            raise ValueError('training_result.export_weights must include left_template and right_template')
        np.savez_compressed(runtime_model_path, left_template=left_template, right_template=right_template)
        parameters = dict(training_result.get('learned_parameters', {}) or {})
        (package_dir / 'parameters.json').write_text(json.dumps(parameters, indent=2, ensure_ascii=False), encoding='utf-8')
        benchmark_manifest_path = package_dir / 'benchmark_manifest.json'
        dataset_hash = str(training_result.get('dataset_hash', '') or self._stable_hash(dict(training_result.get('spec', {}))))
        training_run_id = str(training_result.get('training_run_id', '') or f'frame_anatomy_keypoint:{dataset_hash[:16]}')
        model_meta = {
            'generated_at': now_text(),
            'package_name': 'frame_anatomy_keypoint_exported',
            'package_version': '2.0.0',
            'backend': 'numpy_template_export',
            'runtime_kind': 'exported_weight_template',
            'task': 'frame_anatomy_points',
            'release_state': str(training_result.get('release_state', 'research_fixture') or 'research_fixture'),
            'clinical_claim': 'non_clinical_research_only',
            'input_contract': 'raw_ultrasound_frame_sequence',
            'runtime_model_path': runtime_model_filename,
            'trainer_backend': str(training_result.get('trainer_backend', 'numpy_baseline') or 'numpy_baseline'),
            'task_name': str(training_result.get('task_name', 'frame_anatomy_keypoint') or 'frame_anatomy_keypoint'),
            'training_metrics': dict(training_result.get('metrics', {}) or {}),
            'training_run_id': training_run_id,
            'dataset_source': str(training_result.get('dataset_source', 'fixture') or 'fixture'),
            'dataset_hash': dataset_hash,
            'strict_runtime_required': True,
        }
        (package_dir / 'model_meta.json').write_text(json.dumps(model_meta, indent=2, ensure_ascii=False), encoding='utf-8')
        write_model_bundle_manifest(
            package_dir,
            build_model_bundle_manifest(
                bundle_id=f'frame_anatomy_keypoint:{package_dir.name}',
                package_name=package_dir.name,
                runtime_profile='clinical_mainline',
                weights_path=runtime_model_filename,
                entrypoint='spine_ultrasound_ui.training.runtime_adapters.frame_anatomy_keypoint',
                parameter_path='parameters.json',
                meta_path='model_meta.json',
                metrics=dict(training_result.get('metrics', {}) or {}),
                training_run_id=training_run_id,
                dataset_source=str(training_result.get('dataset_source', 'fixture') or 'fixture'),
                dataset_hash=dataset_hash,
                trainer_backend=str(training_result.get('trainer_backend', 'numpy_baseline') or 'numpy_baseline'),
                release_state=str(model_meta.get('release_state', 'research_fixture') or 'research_fixture'),
                clinical_claim='non_clinical_research_only',
                benchmark_manifest_path='',
                strict_runtime_required=True,
            ),
        )
        dataset = FrameAnatomyPointDataset(spec.dataset_manifest)
        case_specs = []
        for index in range(len(dataset)):
            sample = dataset[index]
            case_specs.append({
                'case_id': sample['case_id'],
                'image_path': sample['image_path'],
                'left': {'x_px': int(sample['left']['x_px']), 'y_px': int(sample['left']['y_px'])},
                'right': {'x_px': int(sample['right']['x_px']), 'y_px': int(sample['right']['y_px'])},
            })
        benchmark = FrameAnatomyBenchmarkService().evaluate_many(package_dir, case_specs)
        benchmark_manifest_path.write_text(json.dumps(benchmark, indent=2, ensure_ascii=False), encoding='utf-8')
        model_meta['benchmark_manifest_path'] = 'benchmark_manifest.json'
        (package_dir / 'model_meta.json').write_text(json.dumps(model_meta, indent=2, ensure_ascii=False), encoding='utf-8')
        write_model_bundle_manifest(
            package_dir,
            build_model_bundle_manifest(
                bundle_id=f'frame_anatomy_keypoint:{package_dir.name}',
                package_name=package_dir.name,
                runtime_profile='clinical_mainline',
                weights_path=runtime_model_filename,
                entrypoint='spine_ultrasound_ui.training.runtime_adapters.frame_anatomy_keypoint',
                parameter_path='parameters.json',
                meta_path='model_meta.json',
                metrics=dict(training_result.get('metrics', {}) or {}),
                training_run_id=training_run_id,
                dataset_source=str(training_result.get('dataset_source', 'fixture') or 'fixture'),
                dataset_hash=dataset_hash,
                trainer_backend=str(training_result.get('trainer_backend', 'numpy_baseline') or 'numpy_baseline'),
                release_state=str(model_meta.get('release_state', 'research_fixture') or 'research_fixture'),
                clinical_claim='non_clinical_research_only',
                benchmark_manifest_path='benchmark_manifest.json',
                strict_runtime_required=True,
            ),
        )
        return {
            'package_dir': str(package_dir),
            'runtime_model_path': str(runtime_model_path),
            'benchmark_manifest_path': str(benchmark_manifest_path),
        }

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode('utf-8')).hexdigest()

    def _dataset_hash(self, dataset: FrameAnatomyPointDataset) -> str:
        parts: list[dict[str, Any]] = []
        for index in range(len(dataset)):
            sample = dataset[index]
            parts.append({
                'case_id': sample['case_id'],
                'image_path': Path(str(sample['image_path'])).name,
                'left': dict(sample['left']),
                'right': dict(sample['right']),
            })
        return self._stable_hash({'cases': parts})

    @staticmethod
    def _extract_patch(image: np.ndarray, x_px: int, y_px: int, patch_radius: int) -> np.ndarray:
        image = np.asarray(image, dtype=np.float32)
        size = patch_radius * 2 + 1
        patch = np.zeros((size, size), dtype=np.float32)
        for row_offset, row in enumerate(range(y_px - patch_radius, y_px + patch_radius + 1)):
            for col_offset, col in enumerate(range(x_px - patch_radius, x_px + patch_radius + 1)):
                if 0 <= row < image.shape[0] and 0 <= col < image.shape[1]:
                    patch[row_offset, col_offset] = image[row, col]
        return patch

    @staticmethod
    def _normalize_template(template: np.ndarray) -> np.ndarray:
        template = np.asarray(template, dtype=np.float32)
        template = template - float(np.mean(template))
        norm = float(np.linalg.norm(template))
        if norm <= 1e-6:
            return np.zeros_like(template, dtype=np.float32)
        return template / norm
