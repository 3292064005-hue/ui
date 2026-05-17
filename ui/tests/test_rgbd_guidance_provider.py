from __future__ import annotations

import numpy as np

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.perception.camera_provider import CameraProvider
from spine_ultrasound_ui.services.perception.guidance_perception_service import GuidancePerceptionService


def test_filesystem_rgbd_guidance_frame_carries_depth_envelope(tmp_path):
    rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    rgb[8:42, 28:36, :] = 220
    depth = np.full((48, 64), 205.0, dtype=np.float32)
    depth += np.linspace(-4.0, 4.0, 48, dtype=np.float32)[:, None]
    source = tmp_path / "frame_001.npz"
    np.savez(source, rgb=rgb, depth_mm=depth, mm_per_pixel_x=0.5, mm_per_pixel_y=0.75)

    frames = CameraProvider().collect_frames(
        experiment_id="EXP_RGBD",
        config=RuntimeConfig(camera_guidance_input_mode="filesystem", camera_guidance_source_path=str(source)),
        calibration_bundle={
            "camera_device_id": "d435i",
            "camera_intrinsics_hash": "intrinsics-hash",
            "camera_intrinsics": {"mm_per_pixel_x": 0.5, "mm_per_pixel_y": 0.75, "frame_type": "rgbd"},
        },
        source_type="camera_only",
    )

    assert len(frames) == 1
    assert frames[0].depth_pixels is not None
    envelope = frames[0].envelope()
    assert envelope["frame_type"] == "rgbd"
    assert envelope["depth_valid_ratio"] == 1.0
    assert envelope["depth_median_mm"] == 205.0


def test_guidance_perception_uses_depth_surface_metrics(tmp_path):
    rgb = np.zeros((48, 64, 3), dtype=np.uint8)
    rgb[8:42, 28:36, :] = 220
    depth = np.full((48, 64), 205.0, dtype=np.float32)
    depth += np.linspace(-8.0, 8.0, 48, dtype=np.float32)[:, None]
    source = tmp_path / "frame_001.npz"
    np.savez(source, rgb=rgb, depth_mm=depth, mm_per_pixel_x=0.5, mm_per_pixel_y=0.75)
    config = RuntimeConfig(camera_guidance_input_mode="filesystem", camera_guidance_source_path=str(source))
    calibration_bundle = {
        "camera_device_id": "d435i",
        "camera_intrinsics_hash": "intrinsics-hash",
        "camera_intrinsics": {"mm_per_pixel_x": 0.5, "mm_per_pixel_y": 0.75, "frame_type": "rgbd"},
    }

    frames = CameraProvider().collect_frames(
        experiment_id="EXP_RGBD",
        config=config,
        calibration_bundle=calibration_bundle,
        source_type="camera_only",
    )
    observation = GuidancePerceptionService().analyze(
        frames=frames,
        config=config,
        calibration_bundle=calibration_bundle,
        source_type="camera_only",
    )

    assert observation.body_surface["model"] == "rgbd_surface_fit_v1"
    assert observation.body_surface["depth_source"] == "depth_frame"
    assert observation.body_surface["depth_valid_ratio"] > 0.9
    assert observation.registration_quality["quality_metrics"]["depth_valid_ratio"] > 0.9
