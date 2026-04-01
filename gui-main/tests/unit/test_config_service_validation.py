from __future__ import annotations

import pytest
import yaml

from robot_sim.application.services.config_service import ConfigService
from robot_sim.infra.schema import SchemaError


def test_config_service_rejects_invalid_solver_config(tmp_path):
    cfg_dir = tmp_path / 'configs'
    cfg_dir.mkdir()
    (cfg_dir / 'solver.yaml').write_text(yaml.safe_dump({
        'ik': {
            'mode': 'dls',
            'min_damping_lambda': 2.0,
            'max_damping_lambda': 0.1,
        }
    }), encoding='utf-8')
    service = ConfigService(cfg_dir)
    with pytest.raises(SchemaError):
        service.load_solver_config()
