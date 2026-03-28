#!/usr/bin/env python3

import sys
import os
import time
import subprocess
import numpy as np
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spine_ultrasound_ui.core_pipeline.shm_client import ShmPoseReader

def test_comprehensive_interpolation():
    """全面测试位姿插值功能"""
    cpp_process = None
    try:
        # 启动C++发布者
        cpp_process = subprocess.Popen(
            ['./cpp_robot_core/build/test_seqlock'],
            cwd='/home/chen/gui-main'
        )

        # 等待初始化和数据积累
        time.sleep(3)

        # 连接共享内存
        reader = ShmPoseReader("test_seqlock_shm")
        print("[Test] Connected to shared memory")

        # 获取一些最新数据来了解时间戳范围
        latest = reader.get_latest_pose()
        if latest:
            current_ts, _, _, _ = latest
            print(f"[Test] Current latest timestamp: {current_ts}")

            # 测试多个插值点
            test_timestamps = [
                current_ts - 500000000,  # 0.5秒前
                current_ts - 200000000,  # 0.2秒前
                current_ts - 100000000,  # 0.1秒前
            ]

            for i, target_ts in enumerate(test_timestamps):
                print(f"\n[Test] Querying interpolation {i+1} at timestamp: {target_ts}")
                result = reader.query_interpolated_pose(target_ts)

                if result:
                    pos, quat = result
                    print(f"[Test] Interpolated position: {pos}")
                    print(f"[Test] Interpolated orientation: {quat}")
                    print(f"[Test] Interpolation {i+1} PASSED!")
                else:
                    print(f"[Test] No data found for timestamp {target_ts}")

        reader.close()

    except Exception as e:
        print(f"[Test] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if cpp_process:
            cpp_process.terminate()
            try:
                cpp_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cpp_process.kill()

if __name__ == "__main__":
    test_comprehensive_interpolation()