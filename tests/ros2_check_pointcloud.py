#!/usr/bin/env python3
"""
Subscribe to /driver/lidar/top on ROS2 and verify bridged PointCloud2 messages.
Run inside the ROS2 bridge container. Exits 0 if at least MIN_MESSAGES received
with expected frame_id and data length; non-zero otherwise.
"""
import argparse
import sys

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2


class PointCloudChecker(Node):
    def __init__(self, topic: str, min_messages: int, expected_frame: str, expected_data_len: int, timeout_sec: float):
        super().__init__("ros2_check_pointcloud")
        self.topic = topic
        self.min_messages = min_messages
        self.expected_frame = expected_frame
        self.expected_data_len = expected_data_len
        self.timeout_sec = timeout_sec
        self.received = 0
        self.last_frame_id = None
        self.last_data_len = None
        self.sub = self.create_subscription(PointCloud2, topic, self.callback, 10)

    def callback(self, msg):
        self.received += 1
        self.last_frame_id = msg.header.frame_id
        if hasattr(msg.data, "__len__"):
            self.last_data_len = len(msg.data)
        else:
            self.last_data_len = len(list(msg.data)) if hasattr(msg.data, "__iter__") else 0

    def run(self):
        import time
        deadline = time.monotonic() + self.timeout_sec
        while rclpy.ok() and time.monotonic() < deadline and self.received < self.min_messages:
            rclpy.spin_once(self, timeout_sec=0.2)
        return self.received >= self.min_messages and (
            self.expected_frame is None or self.last_frame_id == self.expected_frame
        ) and (
            self.expected_data_len is None or self.last_data_len == self.expected_data_len
        )


def main():
    parser = argparse.ArgumentParser(description="Check PointCloud2 on ROS2 side after bridge")
    parser.add_argument("--topic", default="/driver/lidar/top", help="Topic to subscribe to")
    parser.add_argument("--min-messages", type=int, default=3, help="Minimum messages to receive")
    parser.add_argument("--expected-frame", default="lidar_top", help="Expected header.frame_id")
    parser.add_argument("--expected-data-len", type=int, default=36, help="Expected data length in bytes")
    parser.add_argument("--timeout", type=float, default=15.0, help="Timeout in seconds")
    args = parser.parse_args()

    rclpy.init()
    node = PointCloudChecker(
        args.topic,
        args.min_messages,
        args.expected_frame,
        args.expected_data_len,
        args.timeout,
    )
    ok = node.run()
    node.destroy_node()
    rclpy.shutdown()
    if ok:
        print(f"[PASS] Received {node.received} message(s), frame_id={node.last_frame_id}, data_len={node.last_data_len}")
        return 0
    print(
        f"[FAIL] received={node.received} (min={args.min_messages}), "
        f"frame_id={node.last_frame_id} (expected={args.expected_frame}), "
        f"data_len={node.last_data_len} (expected={args.expected_data_len})",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
