#!/usr/bin/env python3
"""
ROS1 side of the ZMQ bridge. Binds ZMQ on 5555 (PUB ros1->ros2) and 5556 (SUB ros2->ros1).
Subscribes to ROS1 /tf, /goal_pose; publishes to ROS1 /map, /control_cmd, /plan.
All imports at module level; uses ROS1Publisher/ROS1Subscriber from ros1_handlers.
"""

import os
import sys
import json
import queue
import threading
import time

import rospy
import zmq

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

from schema import ROS1_TO_ROS2_TOPICS, ROS2_TO_ROS1_TOPICS, SEND_QUEUE_MAXSIZE, decode_message
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

    # Per-topic queues (schema-driven): each topic has its own queue; one sender round-robins.
    send_queues = {
        topic: queue.Queue(maxsize=SEND_QUEUE_MAXSIZE)
        for topic in ROS1_TO_ROS2_TOPICS
    }
    send_topics = sorted(send_queues.keys())
    _shutdown = threading.Event()

    def zmq_sender_loop():
        while not _shutdown.is_set():
            sent_any = False
            for topic in send_topics:
                try:
                    item = send_queues[topic].get_nowait()
                except queue.Empty:
                    continue
                if item is None:
                    continue
                msg_type, body = item
                try:
                    pub_sock.send_multipart([
                        topic.encode("utf-8"),
                        msg_type.encode("utf-8"),
                        body,
                    ])
                    sent_any = True
                except Exception as e:
                    rospy.logerr_throttle(5, "ROS1 relay ZMQ send %s: %s", topic, e)
            if not sent_any:
                time.sleep(0.001)

    def send_to_zmq(topic: str, msg_type: str, body: bytes) -> None:
        q = send_queues.get(topic)
        if q is None:
            return
        try:
            q.put_nowait((msg_type, body))
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

    try:
        rospy.spin()
    finally:
        _shutdown.set()
        for q in send_queues.values():
            try:
                q.put_nowait(None)
            except queue.Full:
                pass
        sender_thread.join(timeout=2.0)
    context.term()


if __name__ == "__main__":
    main()
