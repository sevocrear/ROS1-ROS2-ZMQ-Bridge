#!/usr/bin/env python3
"""
ROS1 side of the ZMQ bridge.  Binds ZMQ on 5555 (PUB ros1->ros2) and 5556 (SUB ros2->ros1).
Subscribes to ROS1 /tf, /goal_pose; publishes to ROS1 /map, /control_cmd, /plan.
All imports at module level; uses ROS1Publisher/ROS1Subscriber from ros1_handlers.
"""

import os
import sys
import queue
import threading

import rospy
import zmq

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

from schema import (
    ROS1_TO_ROS2_TOPICS, ROS2_TO_ROS1_TOPICS,
    SEND_QUEUE_MAXSIZE, ZMQ_HWM, TOPIC_TO_TYPE,
    decode_message, _env_int,
)
from ros1_handlers import create_ros1_publishers, create_ros1_subscribers

PORT_ROS1_TO_ROS2 = _env_int("BRIDGE_ZMQ_PORT_ROS1_TO_ROS2", 5555)
PORT_ROS2_TO_ROS1 = _env_int("BRIDGE_ZMQ_PORT_ROS2_TO_ROS1", 5556)

# Pre-encode ZMQ topic/type frames (avoids per-message string allocation).
_TOPIC_FRAMES = {
    topic: (topic.encode("utf-8"), TOPIC_TO_TYPE[topic].encode("utf-8"))
    for topic in ROS1_TO_ROS2_TOPICS
}


def main():
    rospy.init_node("ros1_bridge_relay", anonymous=False)

    publishers = {p.topic: p for p in create_ros1_publishers()}
    subscribers = create_ros1_subscribers()

    context = zmq.Context()

    sub_sock = context.socket(zmq.SUB)
    sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
    sub_sock.setsockopt(zmq.RCVHWM, ZMQ_HWM)
    sub_sock.setsockopt(zmq.RCVTIMEO, 5000)
    sub_sock.setsockopt(zmq.LINGER, 0)
    sub_sock.bind(f"tcp://*:{PORT_ROS2_TO_ROS1}")

    pub_sock = context.socket(zmq.PUB)
    pub_sock.setsockopt(zmq.SNDHWM, ZMQ_HWM)
    pub_sock.setsockopt(zmq.LINGER, 100)
    pub_sock.bind(f"tcp://*:{PORT_ROS1_TO_ROS2}")

    # Single shared send queue — blocking get() eliminates the 1 kHz busy-wait.
    send_queue = queue.Queue(
        maxsize=SEND_QUEUE_MAXSIZE * max(len(ROS1_TO_ROS2_TOPICS), 1)
    )
    _shutdown = threading.Event()

    def zmq_sender_loop():
        while not _shutdown.is_set():
            try:
                item = send_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if item is None:
                break
            topic_b, type_b, body = item
            try:
                pub_sock.send_multipart([topic_b, type_b, body])
            except Exception as e:
                rospy.logerr_throttle(5, "ROS1 relay ZMQ send: %s", e)

    def send_to_zmq(topic: str, msg_type: str, body: bytes) -> None:
        frames = _TOPIC_FRAMES.get(topic)
        if frames is None:
            return
        try:
            send_queue.put_nowait((*frames, body))
        except queue.Full:
            rospy.logwarn_throttle(2, "ROS1 relay: send queue full for %s, dropping", topic)

    sender_thread = threading.Thread(target=zmq_sender_loop, daemon=True)
    sender_thread.start()

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
            except zmq.Again:
                continue
            except zmq.ZMQError as e:
                if _shutdown.is_set():
                    break
                rospy.logerr_throttle(5, "ROS1 relay ZMQ recv error: %s", e)
                continue
            if len(frames) < 3:
                continue
            topic = frames[0].decode("utf-8")
            if topic not in ROS2_TO_ROS1_TOPICS:
                continue
            publisher = publishers.get(topic)
            if not publisher:
                continue
            try:
                payload = decode_message(frames[2])
            except (ValueError, UnicodeDecodeError) as e:
                rospy.logwarn_throttle(5, "ROS1 relay: invalid JSON for %s: %s", topic, e)
                continue
            try:
                publisher.publish_from_dict(payload)
            except Exception as e:
                rospy.logerr_throttle(5, "ROS1 relay: publish error for %s: %s", topic, e)
            rospy.logdebug_throttle(2, "ROS1 relay: published %s from ZMQ", topic)

    recv_thread = threading.Thread(target=zmq_receive_loop, daemon=True)
    recv_thread.start()

    try:
        rospy.spin()
    finally:
        _shutdown.set()
        try:
            send_queue.put_nowait(None)
        except queue.Full:
            pass
        sender_thread.join(timeout=2.0)
        pub_sock.close()
        sub_sock.close()
        context.term()


if __name__ == "__main__":
    main()
