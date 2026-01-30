"""
Abstract interfaces for bridge endpoints. No rospy/rclpy imports so both relays can use them.
Concrete implementations live in ros1_handlers and ros2_handlers.
"""

from abc import ABC, abstractmethod
from typing import Callable


# Type for ZMQ sender: (topic: str, msg_type: str, body: bytes) -> None
ZmqSender = Callable[[str, str, bytes], None]


class ROS1Publisher(ABC):
    """Publishes to a ROS1 topic from a JSON-serializable dict (ZMQ -> ROS1)."""

    @property
    @abstractmethod
    def topic(self) -> str:
        pass

    @abstractmethod
    def publish_from_dict(self, payload: dict) -> None:
        """Deserialize payload and publish to ROS1."""
        pass


class ROS1Subscriber(ABC):
    """Subscribes to a ROS1 topic and forwards messages to ZMQ (ROS1 -> ZMQ)."""

    @property
    @abstractmethod
    def topic(self) -> str:
        pass

    @abstractmethod
    def register(self, sender: ZmqSender) -> None:
        """Register with ROS1; on each message call sender(topic, msg_type, body)."""
        pass


class ROS2Publisher(ABC):
    """Publishes to a ROS2 topic from a JSON-serializable dict (ZMQ -> ROS2)."""

    @property
    @abstractmethod
    def topic(self) -> str:
        pass

    @abstractmethod
    def publish_from_dict(self, payload: dict) -> None:
        """Deserialize payload and publish to ROS2."""
        pass


class ROS2Subscriber(ABC):
    """Subscribes to a ROS2 topic and forwards messages to ZMQ (ROS2 -> ZMQ)."""

    @property
    @abstractmethod
    def topic(self) -> str:
        pass

    @abstractmethod
    def register(self, sender: ZmqSender) -> None:
        """Register with ROS2; on each message call sender(topic, msg_type, body)."""
        pass
