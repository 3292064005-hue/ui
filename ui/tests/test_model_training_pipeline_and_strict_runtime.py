import json
import subprocess
import sys
from pathlib import Path

from spine_ultrasound_ui.services.reconstruction.bone_segmentation_inference_service import BoneSegmentationInferenceService
from spine_ultrasound_ui.services.reconstruction.spine_curve_reconstruction_service import SpineCurveReconstructionService
from spine_ultrasound_ui.training.runtime_adapters.keypoint_runtime_adapter import KeypointRuntimeAdapter
from spine_ultrasound_ui.training.runtime_adapters.ranking_runtime_adapter import RankingRuntimeAdapter
from spine_ultrasound_ui.training.runtime_adapters.segmentation_runtime_adapter import SegmentationRuntimeAdapter


ROOT = Path(__file__).resolve().parents[1]


def _run_pipeline(tmp_path: Path, *args: str) -> dict:
    proc = subprocess.run(
        [sys.executable, str(ROOT / 'scripts' / 'run_model_training_pipeline.py'), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    return json.loads(Path(payload['summary_path']).read_text(encoding='utf-8'))


def test_fixture_training_pipeline_exports_runtime_packages(tmp_path: Path) -> None:
    output_root = tmp_path / 'training'
    summary = _run_pipeline(tmp_path, '--task', 'all', '--backend', 'numpy_baseline', '--output-root', str(output_root))
    results = {item['task']: item for item in summary['results']}

    assert set(results) == {'frame_anatomy_keypoint', 'lamina_seg', 'lamina_keypoint', 'uca_rank'}
    for result in results.values():
        assert result['mode'] == 'exported_package'
        assert Path(result['package_dir']).exists()
        assert Path(result['bundle_manifest_path'] if 'bundle_manifest_path' in result else Path(result['package_dir']) / 'bundle_manifest.json').exists()

    seg = SegmentationRuntimeAdapter()
    seg.load(results['lamina_seg']['package_dir'])
    keypoint = KeypointRuntimeAdapter()
    keypoint.load(results['lamina_keypoint']['package_dir'])
    frame = KeypointRuntimeAdapter()
    frame.load(results['frame_anatomy_keypoint']['package_dir'])
    rank = RankingRuntimeAdapter()
    rank.load(results['uca_rank']['package_dir'])

    assert seg.is_loaded
    assert keypoint.is_loaded
    assert frame.is_loaded
    assert rank.is_loaded


def test_backend_pipeline_emits_requests_without_fake_weights(tmp_path: Path) -> None:
    output_root = tmp_path / 'training'
    summary = _run_pipeline(tmp_path, '--task', 'lamina_seg', '--backend', 'monai', '--output-root', str(output_root))
    result = summary['results'][0]
    request_path = Path(result['training_request_path'])
    assert result['mode'] == 'backend_request'
    assert request_path.exists()
    request = json.loads(request_path.read_text(encoding='utf-8'))
    assert request['trainer_backend'] == 'monai'
    assert request['dependency_status']['available'] in {True, False}
    assert not (output_root / 'packages' / 'lamina_seg' / 'parameters.json').exists()


def test_strict_model_runtime_blocks_reconstruction_with_evidence(tmp_path: Path) -> None:
    bad_config = tmp_path / 'missing_lamina_seg_runtime.yaml'
    reconstruction = SpineCurveReconstructionService(
        bone_segmentation_service=BoneSegmentationInferenceService(runtime_model_config=bad_config),
    )
    result = reconstruction.reconstruct({
        'session_id': 'session-model-blocked',
        'experiment_id': 'exp-model-blocked',
        'selected_rows': [],
        'source_counts': {'selected_rows': 0, 'authoritative_rows': 0},
        'manual_review_reasons': ['no_reconstructable_rows'],
    })

    summary = result['reconstruction_summary']
    assert summary['reconstruction_status'] == 'blocked'
    assert summary['closure_verdict'] == 'blocked'
    assert any('model_runtime_blocked:lamina_seg' in reason for reason in summary['hard_blockers'])
    assert result['reconstruction_evidence']['runtime_models']['bone_segmentation']['runtime_kind'] == 'blocked'
