from robot_sim.app.container import build_container


def test_importer_descriptor_contains_fidelity(project_root):
    container = build_container(project_root)
    descriptor = {d.importer_id: d for d in container.importer_registry.descriptors()}['urdf_skeleton']
    assert descriptor.metadata['fidelity'] == 'approximate'
