from robot_sim.core.collision.capsule_backend import CapsuleCollisionBackend


def test_capsule_backend_contract_reports_unavailable_status():
    backend = CapsuleCollisionBackend()
    payload = backend.check_state_collision()
    assert backend.backend_id == 'capsule'
    assert payload['backend_id'] == 'capsule'
    assert payload['availability'] == 'unavailable'
    assert payload['fallback_backend'] == 'aabb'
