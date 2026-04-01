from robot_sim.domain.error_projection import TaskErrorMapper
from robot_sim.domain.errors import IKDidNotConvergeError


def test_task_error_mapper_projects_robot_sim_error():
    mapper = TaskErrorMapper()
    presentation = mapper.map_exception(IKDidNotConvergeError('solve failed'))
    assert presentation.title == '逆运动学未收敛'
    assert presentation.error_code == 'ik_did_not_converge'
