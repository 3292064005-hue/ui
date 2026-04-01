from __future__ import annotations

import json
import zipfile

from robot_sim.application.services.package_service import PackageService


def test_package_service_exports_zip_with_manifest(tmp_path):
    service = PackageService(tmp_path)
    payload = tmp_path / 'a.json'
    payload.write_text('{"ok": true}', encoding='utf-8')
    manifest = service.build_manifest(robot_id='planar', files=[payload.name])
    path = service.export_package('bundle.zip', [payload], manifest)
    assert path.exists()
    with zipfile.ZipFile(path) as zf:
        assert 'a.json' in zf.namelist()
        meta = json.loads(zf.read('manifest.json').decode('utf-8'))
        assert meta['robot_id'] == 'planar'
