from __future__ import annotations

from pathlib import Path

from robot_sim.application.services.package_service import PackageService


class ExportPackageUseCase:
    def __init__(self, package_service: PackageService) -> None:
        self._package_service = package_service

    def execute(self, name: str, files: list[Path], **manifest_kwargs):
        manifest = self._package_service.build_manifest(files=[file.name for file in files], **manifest_kwargs)
        return self._package_service.export_package(name, files, manifest)
