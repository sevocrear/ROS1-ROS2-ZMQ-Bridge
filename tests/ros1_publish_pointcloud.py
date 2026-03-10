#!/usr/bin/env python3
"""
Publish a minimal synthetic sensor_msgs/PointCloud2 on /driver/lidar/top for bridge testing.
Run inside the ROS1 bridge container (or any ROS1 environment with rospy and sensor_msgs).
Usage: python3 ros1_publish_pointcloud.py [--rate RATE]
"""
import argparse
import sys

import rospy
from sensor_msgs.msg import PointCloud2, PointField


def main():
    parser = argparse.ArgumentParser(description="Publish synthetic PointCloud2 for bridge test")
    parser.add_argument("--topic", default="/driver/lidar/top", help="Topic to publish to")
    parser.add_argument("--rate", type=float, default=5.0, help="Publish rate in Hz")
    parser.add_argument("--frame", default="lidar_top", help="Frame ID in header")
    args = parser.parse_args()

    rospy.init_node("ros1_publish_pointcloud", anonymous=True)
    pub = rospy.Publisher(args.topic, PointCloud2, queue_size=10)

    # Minimal PointCloud2: 3 points, each with x,y,z (float32) = 12 bytes per point
    msg = PointCloud2()
    msg.header.frame_id = args.frame
    msg.height = 1
    msg.width = 3
    msg.is_dense = True
    msg.is_bigendian = False
    msg.point_step = 12
    msg.row_step = 36
    msg.fields.append(PointField(name="x", offset=0, datatype=PointField.FLOAT32, count=1))
    msg.fields.append(PointField(name="y", offset=4, datatype=PointField.FLOAT32, count=1))
    msg.fields.append(PointField(name="z", offset=8, datatype=PointField.FLOAT32, count=1))
    # 3 points * 12 bytes = 36 bytes; first point (1.0, 2.0, 3.0) for verification
    import struct
    payload = bytearray(36)
    struct.pack_into("<f", payload, 0, 1.0)
    struct.pack_into("<f", payload, 4, 2.0)
    struct.pack_into("<f", payload, 8, 3.0)
    msg.data = list(payload)

    rate = rospy.Rate(args.rate)
    while not rospy.is_shutdown():
        msg.header.stamp = rospy.Time.now()
        pub.publish(msg)
        rate.sleep()

    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
