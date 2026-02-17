"""
Shared JSON schema for bridge messages (topic + type + payload).
Used by both ros1_relay and ros2_relay; payload is a dict compatible with ROS1/ROS2 message fields.
"""

import json
import os


def _env_int(name: str, default: int) -> int:
    """Read an integer from an environment variable with validation."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Invalid integer for env var {name}={raw!r}")


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

# Max items in the shared send queue.
SEND_QUEUE_MAXSIZE = _env_int("BRIDGE_SEND_QUEUE_MAXSIZE", 100)

# ZMQ high-water mark for PUB/SUB sockets (per-socket buffer depth).
ZMQ_HWM = _env_int("BRIDGE_ZMQ_HWM", 500)

# Seconds to wait after ZMQ connect for the slow-joiner handshake.
ZMQ_CONNECT_DELAY = float(os.environ.get("BRIDGE_ZMQ_CONNECT_DELAY", "1.0"))

# Latched / TRANSIENT_LOCAL topics: late joiners receive last message (e.g. /map from map_server)
LATCHED_TOPICS = frozenset(["/map"])


def decode_message(body: bytes) -> dict:
    """Decode ZMQ body to dict."""
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))
