from robot_sim.model.robot_geometry import RobotGeometry
from robot_sim.model.robot_model_bundle import RobotModelBundle


def test_robot_model_bundle_holds_spec_and_geometry(planar_spec):
    bundle = RobotModelBundle(spec=planar_spec, geometry=RobotGeometry.simple_capsules(planar_spec.dof), fidelity='native', importer_id='yaml')
    assert bundle.spec.dof == 2
    assert bundle.geometry is not None
