from __future__ import annotations
from pathlib import Path
import pytest

from robot_sim.application.services.robot_registry import RobotRegistry

@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]

@pytest.fixture
def planar_spec(project_root):
    return RobotRegistry(project_root / "configs" / "robots").load("planar_2dof")

@pytest.fixture
def puma_spec(project_root):
    return RobotRegistry(project_root / "configs" / "robots").load("puma_like_6dof")
