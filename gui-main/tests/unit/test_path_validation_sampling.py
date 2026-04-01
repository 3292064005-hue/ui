from robot_sim.core.collision.path_validation import sample_segment_count


def test_path_validation_sampling_count():
    assert sample_segment_count(5, samples_per_segment=3) == 12
