from robot_sim.presentation.playback_render_scheduler import PlaybackRenderScheduler


def test_playback_render_scheduler_coalesces_latest_frame():
    scheduler = PlaybackRenderScheduler()
    flushed = []
    scheduler.flushed.connect(lambda frame, live: flushed.append((frame, live)))
    scheduler.schedule('frame-1', live=False, immediate=False)
    scheduler.schedule('frame-2', live=True, immediate=False)
    scheduler.flush()
    assert flushed == [('frame-2', True)]
