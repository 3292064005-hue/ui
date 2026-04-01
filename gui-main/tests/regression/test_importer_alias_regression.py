from robot_sim.app.container import build_container


def test_importer_alias_urdf_maps_to_canonical_urdf_skeleton(tmp_path):
    container = build_container(tmp_path)
    importer = container.importer_registry.resolve('urdf')
    canonical = container.importer_registry.resolve('urdf_skeleton')
    assert importer is canonical
