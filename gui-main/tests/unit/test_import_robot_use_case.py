from __future__ import annotations


from robot_sim.application.registries.importer_registry import ImporterRegistry, URDFRobotImporter, YAMLRobotImporter
from robot_sim.application.services.robot_registry import RobotRegistry
from robot_sim.application.use_cases.import_robot import ImportRobotUseCase


def test_import_robot_use_case_loads_yaml(project_root, tmp_path):
    registry = RobotRegistry(project_root / 'configs' / 'robots')
    importer_registry = ImporterRegistry()
    importer_registry.register('yaml', YAMLRobotImporter(registry))
    uc = ImportRobotUseCase(importer_registry)
    source = project_root / 'configs' / 'robots' / 'planar_2dof.yaml'
    spec = uc.execute(source, importer_id='yaml')
    assert spec.dof == 2
    assert spec.label.lower().startswith('planar')


def test_import_robot_use_case_loads_simple_urdf(tmp_path):
    urdf = tmp_path / 'simple.urdf'
    urdf.write_text('''<robot name="simple"><link name="base"/><link name="l1"/><link name="l2"/>
    <joint name="j1" type="revolute"><origin xyz="1 0 0" rpy="0 0 0"/><limit lower="-1.57" upper="1.57"/></joint>
    <joint name="j2" type="revolute"><origin xyz="1 0 0" rpy="0 0 0"/><limit lower="-1.0" upper="1.0"/></joint></robot>''', encoding='utf-8')
    importer_registry = ImporterRegistry()
    importer_registry.register('urdf', URDFRobotImporter())
    uc = ImportRobotUseCase(importer_registry)
    spec = uc.execute(urdf, importer_id='urdf')
    assert spec.dof == 2
    assert spec.metadata['importer'] == 'urdf'
