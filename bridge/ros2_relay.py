#!/usr/bin/env python3
"""
ROS2 side of the ZMQ bridge. Connects to peer (ros1_relay) on 5555 (SUB) and 5556 (PUB).
Subscribes to ROS2 /map, /control_cmd, /plan; publishes to ROS2 /tf, /goal_pose.
All imports at module level; uses ROS2Publisher/ROS2Subscriber from ros2_handlers.
"""

import os
import sys
import queue
import threading
import time

import rclpy
import zmq

BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
if BRIDGE_DIR not in sys.path:
    sys.path.insert(0, BRIDGE_DIR)

from rclpy.node import Node
from schema import ROS1_TO_ROS2_TOPICS, ROS2_TO_ROS1_TOPICS, SEND_QUEUE_MAXSIZE, decode_message
from ros2_handlers import create_ros2_publishers, create_ros2_subscribers

PEER_HOST = os.environ.get("BRIDGE_PEER_HOST", "127.0.0.1")
PORT_ROS1_TO_ROS2 = int(os.environ.get("BRIDGE_ZMQ_PORT_ROS1_TO_ROS2", "5555"))
PORT_ROS2_TO_ROS1 = int(os.environ.get("BRIDGE_ZMQ_PORT_ROS2_TO_ROS1", "5556"))


class ROS2BridgeRelay(Node):
    """Relay node: ZMQ to/from ROS2 via handler interfaces."""

    def __init__(self):
        super().__init__("ros2_bridge_relay")
        self._zmq_context = zmq.Context()
        self.pub_sock = self._zmq_context.socket(zmq.PUB)
        self.pub_sock.setsockopt(zmq.SNDHWM, 10)
        self.pub_sock.connect(f"tcp://{PEER_HOST}:{PORT_ROS2_TO_ROS1}")
        self.sub_sock = self._zmq_context.socket(zmq.SUB)
        self.sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
        self.sub_sock.setsockopt(zmq.RCVHWM, 10)
        self.sub_sock.connect(f"tcp://{PEER_HOST}:{PORT_ROS1_TO_ROS2}")
        self.sub_sock.setsockopt(zmq.RCVTIMEO, 5000)
        # Allow ZMQ connections to establish (slow joiner: SUB must connect before PUB sends)
        time.sleep(1.0)

        # Per-topic queues (schema-driven): each topic has its own queue; one sender round-robins.
        self._send_queues = {
            topic: queue.Queue(maxsize=SEND_QUEUE_MAXSIZE)
            for topic in ROS2_TO_ROS1_TOPICS
        }
        self._send_topics = sorted(self._send_queues.keys())
        self._send_shutdown = threading.Event()
        self._sender_thread = threading.Thread(target=self._zmq_sender_loop, daemon=True)
        self._sender_thread.start()

        self._publishers = {p.topic: p for p in create_ros2_publishers(self)}
        for sub in create_ros2_subscribers(self):
            sub.register(self._send_to_zmq)

        self.get_logger().info(f"ROS2 relay: ZMQ connect to {PEER_HOST} (SUB {PORT_ROS1_TO_ROS2}, PUB {PORT_ROS2_TO_ROS1})")

    def _zmq_sender_loop(self):
        while not self._send_shutdown.is_set():
            sent_any = False
            for topic in self._send_topics:
                try:
                    item = self._send_queues[topic].get_nowait()
                except queue.Empty:
                    continue
                if item is None:
                    continue
                msg_type, body = item
                try:
                    self.pub_sock.send_multipart([
                        topic.encode("utf-8"),
                        msg_type.encode("utf-8"),
                        body,
                    ])
                    sent_any = True
                except Exception as e:
                    self.get_logger().error("ROS2 relay ZMQ send %s: %s" % (topic, e))
            if not sent_any:
                time.sleep(0.001)

    def _send_to_zmq(self, topic: str, msg_type: str, body: bytes) -> None:
        q = self._send_queues.get(topic)
        if q is None:
            return
        try:
            q.put_nowait((msg_type, body))
        except queue.Full:
            self.get_logger().warning("ROS2 relay: send queue full for %s, dropping" % topic)

    def run_zmq_receive_loop(self):
        while rclpy.ok():
            try:
                frames = self.sub_sock.recv_multipart()
            except zmq.Again:
                continue
            except Exception as e:
                self.get_logger().error("ROS2 relay ZMQ recv: %s" % e)
                continue
            if len(frames) != 3:
                self.get_logger().warning(
                    "ROS2 relay: ignoring ZMQ message with %d frames (expected 3)",
                    len(frames),
                )
                continue
            topic = frames[0].decode("utf-8")
            _msg_type = frames[1].decode("utf-8")
            body = frames[2]
            if topic not in ROS1_TO_ROS2_TOPICS:
                continue
            publisher = self._publishers.get(topic)
            if not publisher:
                continue
            try:
                payload = decode_message(body)
            except (ValueError, UnicodeDecodeError) as e:
                self.get_logger().warning("ROS2 relay: invalid ZMQ body for %s: %s" % (topic, e))
                continue
            publisher.publish_from_dict(payload)

    def destroy_node(self, *args, **kwargs):
        self._send_shutdown.set()
        for q in self._send_queues.values():
            try:
                q.put_nowait(None)
            except queue.Full:
                pass
        self._sender_thread.join(timeout=2.0)
        self._zmq_context.term()
        super().destroy_node(*args, **kwargs)


def main(args=None):
    rclpy.init(args=args)
    node = ROS2BridgeRelay()
    try:
        t = threading.Thread(target=node.run_zmq_receive_loop, daemon=True)
        t.start()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
