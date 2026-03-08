"""
Concrete ROS1 bridge handlers. Builds ROS1Publisher and ROS1Subscriber from
schema + ros1_serializer.
All imports at module level.
"""

import json
from typing import List

import rospy

from ackermann_msgs.msg import AckermannDriveStamped
from can_msgs.msg import Frame
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from tf2_msgs.msg import TFMessage

from interfaces import ROS1Publisher, ROS1Subscriber, ZmqSender
from schema import (
    LATCHED_TOPICS,
    ROS1_PUBLISHER_QUEUE_SIZE_DEFAULT,
    ROS1_PUBLISHER_QUEUE_SIZE_OVERRIDES,
    ROS1_SUBSCRIBER_QUEUE_SIZE_DEFAULT,
    ROS1_SUBSCRIBER_QUEUE_SIZE_OVERRIDES,
    ROS1_TO_ROS2_TOPICS,
    ROS2_TO_ROS1_TOPICS,
    TOPIC_TO_TYPE,
)
import ros1_serializer


# Message type string (from schema) -> ROS1 message class
TYPE_TO_ROS1_MSG = {
    "ackermann_msgs/msg/AckermannDriveStamped": AckermannDriveStamped,
    "can_msgs/msg/Frame": Frame,
    "geometry_msgs/msg/PoseStamped": PoseStamped,
    "nav_msgs/msg/Path": Path,
    "nav_msgs/msg/OccupancyGrid": OccupancyGrid,
    "nav_msgs/msg/Odometry": Odometry,
    "tf2_msgs/msg/TFMessage": TFMessage,
}

# Topic -> ROS1 message class (derived from schema so topic names can change)
TOPIC_TO_ROS1_MSG = {
    topic: TYPE_TO_ROS1_MSG[msg_type]
    for topic, msg_type in TOPIC_TO_TYPE.items()
    if msg_type in TYPE_TO_ROS1_MSG
}


class ROS1PublisherImpl(ROS1Publisher):
    """Publishes to ROS1 from ZMQ payload (ros2->ros1)."""

    def __init__(self, topic: str, publisher: rospy.Publisher):
        self._topic = topic
        self._publisher = publisher
        self._msg_class = TOPIC_TO_ROS1_MSG[topic]
    @property
    def topic(self) -> str:
        return self._topic

    def publish_from_dict(self, payload: dict) -> None:
        msg = ros1_serializer.deserialize_ros1(self._topic, payload, self._msg_class)
        self._publisher.publish(msg)


class ROS1SubscriberImpl(ROS1Subscriber):
    """Subscribes to ROS1 and forwards to ZMQ (ros1->ros2)."""

    def __init__(self, topic: str, msg_class: type):
        self._topic = topic
        self._msg_class = msg_class
    @property
    def topic(self) -> str:
        return self._topic

    def register(self, sender: ZmqSender) -> None:
        def callback(msg):
            try:
                payload = ros1_serializer.serialize_ros1(self._topic, msg)
                msg_type = TOPIC_TO_TYPE[self._topic]
                body = json.dumps(payload).encode("utf-8")
                sender(self._topic, msg_type, body)
            except Exception as e:
                rospy.logerr_throttle(5, "ROS1 bridge subscriber %s: %s", self._topic, e)
        queue_size = ROS1_SUBSCRIBER_QUEUE_SIZE_OVERRIDES.get(
            self._topic,
            ROS1_SUBSCRIBER_QUEUE_SIZE_DEFAULT,
        )
        rospy.Subscriber(self._topic, self._msg_class, callback, queue_size=queue_size)
        print(f"ROS1 bridge subscriber created for topic: {self._topic}")

def create_ros1_publishers() -> List[ROS1Publisher]:
    """Build one ROS1Publisher per ROS2->ROS1 topic. Latched for LATCHED_TOPICS (e.g. /map)."""
    out = []
    for topic in sorted(ROS2_TO_ROS1_TOPICS):
        msg_class = TOPIC_TO_ROS1_MSG[topic]
        latch = topic in LATCHED_TOPICS
        queue_size = ROS1_PUBLISHER_QUEUE_SIZE_OVERRIDES.get(
            topic,
            ROS1_PUBLISHER_QUEUE_SIZE_DEFAULT,
        )
        pub = rospy.Publisher(topic, msg_class, queue_size=queue_size, latch=latch)
        out.append(ROS1PublisherImpl(topic, pub))
        print(f"ROS1 bridge publisher created for topic: {topic}")
    return out


def create_ros1_subscribers() -> List[ROS1Subscriber]:
    """Build one ROS1Subscriber per ROS1->ROS2 topic."""
    return [ROS1SubscriberImpl(topic, TOPIC_TO_ROS1_MSG[topic]) for topic in sorted(ROS1_TO_ROS2_TOPICS)]
