#!/usr/bin/env python3
"""
ROS2 side of the ZMQ bridge.  Connects to peer (ros1_relay) on 5555 (SUB) and 5556 (PUB).
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
from config_utils import SEND_QUEUE_MAXSIZE, ZMQ_CONNECT_DELAY, ZMQ_HWM, env_int
from json_utils import decode_message
from schema import ROS1_TO_ROS2_TOPICS, ROS2_TO_ROS1_TOPICS, TOPIC_TO_TYPE
from ros2_handlers import create_ros2_publishers, create_ros2_subscribers

PEER_HOST = os.environ.get("BRIDGE_PEER_HOST", "127.0.0.1")
PORT_ROS1_TO_ROS2 = env_int("BRIDGE_ZMQ_PORT_ROS1_TO_ROS2", 5555)
PORT_ROS2_TO_ROS1 = env_int("BRIDGE_ZMQ_PORT_ROS2_TO_ROS1", 5556)

# Pre-encode ZMQ topic/type frames (avoids per-message string allocation).
_TOPIC_FRAMES = {
    topic: (topic.encode("utf-8"), TOPIC_TO_TYPE[topic].encode("utf-8"))
    for topic in ROS2_TO_ROS1_TOPICS
}


class ROS2BridgeRelay(Node):
    """Relay node: ZMQ to/from ROS2 via handler interfaces."""

    def __init__(self):
        super().__init__("ros2_bridge_relay")

        # --- ZMQ sockets ---
        self._zmq_context = zmq.Context()

        self.pub_sock = self._zmq_context.socket(zmq.PUB)
        self.pub_sock.setsockopt(zmq.SNDHWM, ZMQ_HWM)
        self.pub_sock.setsockopt(zmq.LINGER, 100)
        self.pub_sock.connect(f"tcp://{PEER_HOST}:{PORT_ROS2_TO_ROS1}")

        self.sub_sock = self._zmq_context.socket(zmq.SUB)
        self.sub_sock.setsockopt(zmq.SUBSCRIBE, b"")
        self.sub_sock.setsockopt(zmq.RCVHWM, ZMQ_HWM)
        self.sub_sock.setsockopt(zmq.RCVTIMEO, 5000)
        self.sub_sock.setsockopt(zmq.LINGER, 0)
        self.sub_sock.connect(f"tcp://{PEER_HOST}:{PORT_ROS1_TO_ROS2}")

        if ZMQ_CONNECT_DELAY > 0:
            time.sleep(ZMQ_CONNECT_DELAY)

        # --- Per-topic send queues (ROS2 callbacks -> ZMQ) ---
        # Each topic gets its own bounded queue so a high-rate topic cannot
        # starve or cause drops for a low-rate topic.
        # A shared Event wakes the sender thread instantly (no busy-wait).
        self._send_queues = {
            topic: queue.Queue(maxsize=SEND_QUEUE_MAXSIZE)
            for topic in ROS2_TO_ROS1_TOPICS
        }
        self._send_topics = sorted(self._send_queues.keys())
        self._send_wake = threading.Event()
        self._send_shutdown = threading.Event()
        self._sender_thread = threading.Thread(
            target=self._zmq_sender_loop, daemon=True
        )
        self._sender_thread.start()

        # --- ROS2 publishers / subscribers ---
        self._publishers = {p.topic: p for p in create_ros2_publishers(self)}
        for sub in create_ros2_subscribers(self):
            sub.register(self._send_to_zmq)

        # Guard condition + queue for thread-safe publishing from ZMQ receive thread.
        # The guard condition wakes the rclpy executor so publishing always runs
        # in the executor thread — no cross-thread rclpy.Publisher.publish() calls.
        self._recv_queue = queue.Queue(maxsize=1000)
        self._recv_guard = self.create_guard_condition(self._drain_recv_queue)

        self.get_logger().info(
            f"ROS2 relay: ZMQ connect to {PEER_HOST} "
            f"(SUB {PORT_ROS1_TO_ROS2}, PUB {PORT_ROS2_TO_ROS1})"
        )

    # ---- ZMQ sender (outgoing: ROS2 -> ZMQ -> ROS1) ----

    def _zmq_sender_loop(self):
        while not self._send_shutdown.is_set():
            self._send_wake.wait(timeout=0.1)
            self._send_wake.clear()
            for topic in self._send_topics:
                q = self._send_queues[topic]
                topic_b, type_b = _TOPIC_FRAMES[topic]
                while True:
                    try:
                        body = q.get_nowait()
                    except queue.Empty:
                        break
                    if body is None:
                        return
                    try:
                        self.pub_sock.send_multipart([topic_b, type_b, body])
                    except Exception as e:
                        self.get_logger().error(
                            "ROS2 relay ZMQ send %s: %s" % (topic, e)
                        )

    def _send_to_zmq(self, topic: str, msg_type: str, body: bytes) -> None:
        q = self._send_queues.get(topic)
        if q is None:
            return
        try:
            q.put_nowait(body)
        except queue.Full:
            self.get_logger().warning(
                "ROS2 relay: send queue full for %s, dropping" % topic
            )
            return
        self._send_wake.set()

    # ---- ZMQ receiver (incoming: ROS1 -> ZMQ -> ROS2) ----

    def _drain_recv_queue(self):
        """Called by rclpy executor when guard condition is triggered."""
        while True:
            try:
                topic, payload = self._recv_queue.get_nowait()
            except queue.Empty:
                break
            publisher = self._publishers.get(topic)
            if not publisher:
                continue
            try:
                publisher.publish_from_dict(payload)
            except Exception as e:
                self.get_logger().error(
                    "ROS2 relay: publish error for %s: %s" % (topic, e)
                )

    def run_zmq_receive_loop(self):
        while rclpy.ok():
            try:
                frames = self.sub_sock.recv_multipart()
            except zmq.Again:
                continue
            except zmq.ZMQError as e:
                if self._send_shutdown.is_set():
                    break
                self.get_logger().error("ROS2 relay ZMQ recv: %s" % e)
                continue
            if len(frames) != 3:
                self.get_logger().warning(
                    "ROS2 relay: ignoring ZMQ message with %d frames (expected 3)"
                    % len(frames)
                )
                continue
            topic = frames[0].decode("utf-8")
            if topic not in ROS1_TO_ROS2_TOPICS:
                continue
            if topic not in self._publishers:
                continue
            try:
                payload = decode_message(frames[2])
            except (ValueError, UnicodeDecodeError) as e:
                self.get_logger().warning(
                    "ROS2 relay: invalid ZMQ body for %s: %s" % (topic, e)
                )
                continue
            try:
                self._recv_queue.put_nowait((topic, payload))
                self._recv_guard.trigger()
            except queue.Full:
                self.get_logger().warning(
                    "ROS2 relay: recv queue full, dropping %s" % topic
                )

    # ---- Cleanup ----

    def destroy_node(self, *args, **kwargs):
        self._send_shutdown.set()
        for q in self._send_queues.values():
            try:
                q.put_nowait(None)
            except queue.Full:
                pass
        self._send_wake.set()
        self._sender_thread.join(timeout=2.0)
        self.pub_sock.close()
        self.sub_sock.close()
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
