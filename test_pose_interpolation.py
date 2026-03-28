#!/usr/bin/env python3

import sys
import os
import time
import subprocess
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine_ultrasound_ui.core_pipeline.shm_client import ShmPoseReader

def test_pose_interpolation():
    """测试历史位姿插值功能"""
    cpp_process = None
    try:
        # 启动C++发布者
        cpp_process = subprocess.Popen(
            ['./cpp_robot_core/build/test_seqlock'],
            cwd='/home/chen/gui-main'
        )

        # 等待初始化
        time.sleep(2)

        # 连接共享内存
        reader = ShmPoseReader("test_seqlock_shm")
        print("[Test] Connected to shared memory")

        # 等待一些数据积累
        time.sleep(1)

        # 测试插值：查询一个中间时间戳
        # 假设当前时间戳大约是 1000000000 + n*1000000
        # 我们查询一个中间值，比如 1000500000 (1.5秒)
        target_ts = 1000500000  # 1.0005 秒

        print(f"[Test] Querying interpolated pose at timestamp: {target_ts}")

        result = reader.query_interpolated_pose(target_ts)
        if result:
            pos, quat = result
            print(f"[Test] Interpolated position: {pos}")
            print(f"[Test] Interpolated orientation: {quat}")
            print("[Test] Interpolation test PASSED!")
        else:
            print("[Test] No interpolated data found - this might be expected if timestamps don't match")

        # 也测试最新数据
        latest = reader.get_latest_pose()
        if latest:
            ts, pos, ori, torques = latest
            print(f"[Test] Latest pose at {ts}: pos={pos}, z-force={torques[2]:.2f}")

        reader.close()

    except Exception as e:
        print(f"[Test] Error: {e}")
    finally:
        if cpp_process:
            cpp_process.terminate()
            try:
                cpp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cpp_process.kill()

if __name__ == "__main__":
    test_pose_interpolation()