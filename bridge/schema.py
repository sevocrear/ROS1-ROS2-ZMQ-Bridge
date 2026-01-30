"""
Shared JSON schema for bridge messages (topic + type + payload).
Used by both ros1_relay and ros2_relay; payload is a dict compatible with ROS1/ROS2 message fields.
"""

import json

# Topic -> message type name (ROS2 style: pkg/msg/Type)
TOPIC_TO_TYPE = {
    "/control_cmd": "ackermann_msgs/msg/AckermannDriveStamped",
    "/goal_pose": "geometry_msgs/msg/PoseStamped",
    "/plan": "nav_msgs/msg/Path",
    "/map": "nav_msgs/msg/OccupancyGrid",
    "/tf": "tf2_msgs/msg/TFMessage",
}

# Direction: which relay publishes to ZMQ (and the other subscribes from ZMQ and publishes to ROS)
ROS1_TO_ROS2_TOPICS = {"/tf", "/goal_pose"}
ROS2_TO_ROS1_TOPICS = {"/map", "/control_cmd", "/plan"}

# Latched / TRANSIENT_LOCAL topics: late joiners receive last message (e.g. /map from map_server)
LATCHED_TOPICS = frozenset(["/map"])


def encode_message(topic: str, msg_type: str, payload: dict) -> bytes:
    """Encode (topic, type, payload) as JSON bytes for ZMQ multipart [topic, type, body]."""
    return json.dumps(payload).encode("utf-8")


def decode_message(body: bytes) -> dict:
    """Decode ZMQ body to dict."""
    return json.loads(body.decode("utf-8"))
