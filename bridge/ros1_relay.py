#!/usr/bin/env python3
"""
ROS1 side of the ZMQ bridge. Binds ZMQ on 5555 (PUB ros1->ros2) and 5556 (SUB ros2->ros1).
Subscribes to ROS1 /tf, /goal_pose; publishes to ROS1 /map, /control_cmd, /plan.
All imports at module level; uses ROS1Publisher/ROS1Subscriber from ros1_handlers.
"""

import os
import sys
import json
import threading

import rospy
import zmq

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

from schema import ROS2_TO_ROS1_TOPICS, decode_message
from ros1_handlers import create_ros1_publishers, create_ros1_subscribers

PORT_ROS1_TO_ROS2 = int(os.environ.get("BRIDGE_ZMQ_PORT_ROS1_TO_ROS2", "5555"))
PORT_ROS2_TO_ROS1 = int(os.environ.get("BRIDGE_ZMQ_PORT_ROS2_TO_ROS1", "5556"))


def main():
    rospy.init_node("ros1_bridge_relay", anonymous=False)

    # Handlers: publishers (ZMQ->ROS1) and subscribers (ROS1->ZMQ)
    publishers = {p.topic: p for p in create_ros1_publishers()}
    subscribers = create_ros1_subscribers()

    # ZMQ: bind SUB to receive from ROS2 relay (ros2->ros1)
    context = zmq.Context()
    sub_sock = context.socket(zmq.SUB)
    sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
    sub_sock.setsockopt(zmq.RCVHWM, 10)
    sub_sock.bind(f"tcp://*:{PORT_ROS2_TO_ROS1}")
    sub_sock.setsockopt(zmq.RCVTIMEO, 5000)

    # ZMQ: bind PUB to send to ROS2 relay (ros1->ros2)
    pub_sock = context.socket(zmq.PUB)
    pub_sock.setsockopt(zmq.SNDHWM, 10)
    pub_sock.bind(f"tcp://*:{PORT_ROS1_TO_ROS2}")

    def send_to_zmq(topic: str, msg_type: str, body: bytes) -> None:
        pub_sock.send_multipart([topic.encode("utf-8"), msg_type.encode("utf-8"), body])

    for sub in subscribers:
        sub.register(send_to_zmq)

    rospy.loginfo(
        "ROS1 relay: ZMQ bind SUB port %s (ros2->ros1), PUB port %s (ros1->ros2)",
        PORT_ROS2_TO_ROS1,
        PORT_ROS1_TO_ROS2,
    )

    def zmq_receive_loop():
        while not rospy.is_shutdown():
            try:
                frames = sub_sock.recv_multipart()
                if len(frames) < 3:
                    continue
                topic = frames[0].decode("utf-8")
                _msg_type = frames[1].decode("utf-8")
                body = frames[2]
                if topic not in ROS2_TO_ROS1_TOPICS:
                    continue
                publisher = publishers.get(topic)
                if not publisher:
                    continue
                payload = decode_message(body)
                publisher.publish_from_dict(payload)
                rospy.loginfo_throttle(2, "ROS1 relay: published %s from ZMQ", topic)
            except zmq.Again:
                continue
            except Exception as e:
                rospy.logerr_throttle(5, "ROS1 relay ZMQ recv: %s", e)

    t = threading.Thread(target=zmq_receive_loop, daemon=True)
    t.start()

    rospy.spin()
    context.term()


if __name__ == "__main__":
    main()
