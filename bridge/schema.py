"""
Shared JSON schema for bridge messages (topic + type + payload).
Used by both ros1_relay and ros2_relay; payload is a dict compatible with ROS1/ROS2 message fields.
"""

import json
import os

# Topic -> message type name (ROS2 style: pkg/msg/Type)
TOPIC_TO_TYPE = {
    "/control_cmd": "ackermann_msgs/msg/AckermannDriveStamped",
    "/move_base_simple/goal": "geometry_msgs/msg/PoseStamped",
    "/move_base/PathPlanner/plan": "nav_msgs/msg/Path",
    "/map": "nav_msgs/msg/OccupancyGrid",
    "/tf": "tf2_msgs/msg/TFMessage",
    "/wheel_odometry/odometry": "nav_msgs/msg/Odometry",
}

# Direction: which relay publishes to ZMQ (and the other subscribes from ZMQ and publishes to ROS)
ROS1_TO_ROS2_TOPICS = {"/tf", "/move_base_simple/goal", "/wheel_odometry/odometry"}
ROS2_TO_ROS1_TOPICS = {"/map", "/control_cmd", "/move_base/PathPlanner/plan"}

# Per-topic send queue max size (each topic gets its own queue).
SEND_QUEUE_MAXSIZE = int(os.environ.get("BRIDGE_SEND_QUEUE_MAXSIZE", "100"))

# Latched / TRANSIENT_LOCAL topics: late joiners receive last message (e.g. /map from map_server)
LATCHED_TOPICS = frozenset(["/map"])


def encode_message(topic: str, msg_type: str, payload: dict) -> bytes:
    """Encode (topic, type, payload) as JSON bytes for ZMQ multipart [topic, type, body]."""
    return json.dumps(payload).encode("utf-8")


def decode_message(body: bytes) -> dict:
    """Decode ZMQ body to dict."""
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))
