#!/usr/bin/env python3
"""
Validate ROS2 OccupancyGrid timestamp round-trip in bridge serializer.
"""

import os
import sys

from nav_msgs.msg import OccupancyGrid


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_DIR = os.path.join(REPO_ROOT, "bridge")
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

import ros2_serializer


def _assert_equal(actual, expected, name):
    if actual != expected:
        raise AssertionError(f"{name} mismatch: actual={actual}, expected={expected}")


def _make_msg():
    msg = OccupancyGrid()
    msg.header.stamp.sec = 1710000123
    msg.header.stamp.nanosec = 987654321
    msg.header.frame_id = "map"
    msg.info.map_load_time.sec = 1709990000
    msg.info.map_load_time.nanosec = 123456789
    msg.info.width = 2
    msg.info.height = 2
    msg.info.resolution = 0.05
    msg.data = [0, 50, 100, -1]
    return msg


def main():
    source = _make_msg()
    payload = ros2_serializer.occupancy_grid_to_dict(source)
    restored = ros2_serializer.dict_to_occupancy_grid(payload, OccupancyGrid)

    _assert_equal(restored.header.stamp.sec, source.header.stamp.sec, "header.stamp.sec")
    _assert_equal(
        restored.header.stamp.nanosec,
        source.header.stamp.nanosec,
        "header.stamp.nanosec",
    )
    _assert_equal(
        restored.info.map_load_time.sec,
        source.info.map_load_time.sec,
        "info.map_load_time.sec",
    )
    _assert_equal(
        restored.info.map_load_time.nanosec,
        source.info.map_load_time.nanosec,
        "info.map_load_time.nanosec",
    )

    print("[PASS] ROS2 OccupancyGrid header/map_load_time timestamps are preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
