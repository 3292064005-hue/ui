from robot_sim.app.container import build_container


def test_yaml_and_urdf_importers_expose_fidelity(project_root):
    container = build_container(project_root)
    descriptors = {d.importer_id: d.metadata for d in container.importer_registry.descriptors()}
    assert descriptors['yaml']['fidelity'] == 'native'
    assert descriptors['urdf_skeleton']['fidelity'] == 'approximate'
