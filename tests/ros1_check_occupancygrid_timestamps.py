#!/usr/bin/env python3
"""
Validate ROS1 OccupancyGrid timestamp round-trip in bridge serializer.
"""

import os
import sys

from nav_msgs.msg import OccupancyGrid


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRIDGE_DIR = os.path.join(REPO_ROOT, "bridge")
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

import ros1_serializer


def _assert_equal(actual, expected, name):
    if actual != expected:
        raise AssertionError(f"{name} mismatch: actual={actual}, expected={expected}")


def _make_msg():
    msg = OccupancyGrid()
    msg.header.stamp.secs = 1710000123
    msg.header.stamp.nsecs = 987654321
    msg.header.frame_id = "map"
    msg.info.map_load_time.secs = 1709990000
    msg.info.map_load_time.nsecs = 123456789
    msg.info.width = 2
    msg.info.height = 2
    msg.info.resolution = 0.05
    msg.data = [0, 50, 100, -1]
    return msg


def main():
    source = _make_msg()
    payload = ros1_serializer.occupancy_grid_to_dict(source)
    restored = ros1_serializer.dict_to_occupancy_grid(payload, OccupancyGrid)

    _assert_equal(restored.header.stamp.secs, source.header.stamp.secs, "header.stamp.secs")
    _assert_equal(restored.header.stamp.nsecs, source.header.stamp.nsecs, "header.stamp.nsecs")
    _assert_equal(
        restored.info.map_load_time.secs,
        source.info.map_load_time.secs,
        "info.map_load_time.secs",
    )
    _assert_equal(
        restored.info.map_load_time.nsecs,
        source.info.map_load_time.nsecs,
        "info.map_load_time.nsecs",
    )

    print("[PASS] ROS1 OccupancyGrid header/map_load_time timestamps are preserved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
