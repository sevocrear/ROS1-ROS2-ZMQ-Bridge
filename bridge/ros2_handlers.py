"""
Concrete ROS2 bridge handlers. Builds ROS2Publisher and ROS2Subscriber from
schema + ros2_serializer.
All imports at module level.
"""

import json
from typing import List

import rclpy
from rclpy.node import Node

from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from tf2_msgs.msg import TFMessage

from interfaces import ROS2Publisher, ROS2Subscriber, ZmqSender
from qos_resolver import resolve_publisher_qos, resolve_subscription_qos
from schema import ROS1_TO_ROS2_TOPICS, ROS2_TO_ROS1_TOPICS, TOPIC_TO_TYPE
import ros2_serializer


# Message type string (from schema) -> ROS2 message class
TYPE_TO_ROS2_MSG = {
    "ackermann_msgs/msg/AckermannDriveStamped": AckermannDriveStamped,
    "geometry_msgs/msg/PoseStamped": PoseStamped,
    "nav_msgs/msg/Path": Path,
    "nav_msgs/msg/OccupancyGrid": OccupancyGrid,
    "nav_msgs/msg/Odometry": Odometry,
    "tf2_msgs/msg/TFMessage": TFMessage,
}

# Topic -> ROS2 message class (derived from schema so topic names can change)
TOPIC_TO_ROS2_MSG = {
    topic: TYPE_TO_ROS2_MSG[msg_type]
    for topic, msg_type in TOPIC_TO_TYPE.items()
    if msg_type in TYPE_TO_ROS2_MSG
}


class ROS2PublisherImpl(ROS2Publisher):
    """Publishes to ROS2 from ZMQ payload (ros1->ros2)."""

    def __init__(self, node: Node, topic: str, publisher: rclpy.publisher.Publisher):
        self._node = node
        self._topic = topic
        self._publisher = publisher
        self._msg_class = TOPIC_TO_ROS2_MSG[topic]

    @property
    def topic(self) -> str:
        return self._topic

    def publish_from_dict(self, payload: dict) -> None:
        msg = ros2_serializer.deserialize_ros2(self._topic, payload, self._msg_class)
        self._publisher.publish(msg)


class ROS2SubscriberImpl(ROS2Subscriber):
    """Subscribes to ROS2 and forwards to ZMQ (ros2->ros1)."""

    def __init__(self, node: Node, topic: str, msg_class: type):
        self._node = node
        self._topic = topic
        self._msg_class = msg_class

    @property
    def topic(self) -> str:
        return self._topic

    def register(self, sender: ZmqSender) -> None:
        def callback(msg):
            try:
                payload = ros2_serializer.serialize_ros2(self._topic, msg)
                msg_type = TOPIC_TO_TYPE[self._topic]
                body = json.dumps(payload).encode("utf-8")
                sender(self._topic, msg_type, body)
            except Exception as e:
                self._node.get_logger().error(f"ROS2 bridge subscriber {self._topic}: {e}")

        qos = resolve_subscription_qos(self._node, self._topic)
        self._node.create_subscription(self._msg_class, self._topic, callback, qos)


def create_ros2_publishers(node: Node) -> List[ROS2Publisher]:
    """Build one ROS2Publisher per ROS1->ROS2 topic."""
    out = []
    for topic in sorted(ROS1_TO_ROS2_TOPICS):
        msg_class = TOPIC_TO_ROS2_MSG[topic]
        qos = resolve_publisher_qos(node, topic)
        pub = node.create_publisher(msg_class, topic, qos)
        out.append(ROS2PublisherImpl(node, topic, pub))
    return out


def create_ros2_subscribers(node: Node) -> List[ROS2Subscriber]:
    """Build one ROS2Subscriber per ROS2->ROS1 topic."""
    return [ROS2SubscriberImpl(node, topic, TOPIC_TO_ROS2_MSG[topic]) for topic in sorted(ROS2_TO_ROS1_TOPICS)]
