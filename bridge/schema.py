"""
User-facing configuration for the ROS1–ROS2 ZMQ bridge.

This module is intentionally kept free of any ROS or ZMQ imports and
contains only static configuration:

- Topic names and message types
- Direction of bridging (ROS1→ROS2 vs ROS2→ROS1)
- Latched topics
- Desired QoS profiles for ROS2 (publishers/subscriptions)
- Queue-size style settings for ROS1

All helper functions and environment-driven values live in separate
modules (e.g. `config_utils.py`, `json_utils.py`, `qos_resolver.py`).
"""

from __future__ import annotations

# Topic -> message type name (ROS2 style: pkg/msg/Type)
TOPIC_TO_TYPE = {
    "/control_cmd": "ackermann_msgs/msg/AckermannDriveStamped",
    "/move_base_simple/goal": "geometry_msgs/msg/PoseStamped",
    "/move_base/PathPlanner/plan": "nav_msgs/msg/Path",
    "/map": "nav_msgs/msg/OccupancyGrid",
    "/received_messages": "can_msgs/msg/Frame",
    "/sent_messages": "can_msgs/msg/Frame",
    "/tf": "tf2_msgs/msg/TFMessage",
    "/wheel_odometry/odometry": "nav_msgs/msg/Odometry",
}

# Direction: which relay publishes to ZMQ (and the other subscribes from ZMQ
# and publishes to the local ROS graph).
ROS1_TO_ROS2_TOPICS = {
    "/received_messages",
    "/tf",
    "/move_base_simple/goal",
    "/wheel_odometry/odometry",
}
ROS2_TO_ROS1_TOPICS = {
    "/map",
    "/control_cmd",
    "/move_base/PathPlanner/plan",
    "/sent_messages",
}

# Latched / TRANSIENT_LOCAL topics: late joiners receive last message
# (e.g. /map from map_server).
LATCHED_TOPICS = frozenset(["/map"])


# ------------------------- ROS2 QoS configuration -----------------------------
#
# QoS settings are described using simple string-based dictionaries so that
# they are easy to read and edit. The resolver in `qos_resolver.py` turns
# these dicts into concrete `QoSProfile` instances and can also merge them
# with QoS discovered from existing publishers/subscribers on the graph.
#
# Allowed values:
#   reliability: "RELIABLE" | "BEST_EFFORT"
#   durability:  "VOLATILE" | "TRANSIENT_LOCAL"
#   history:     "KEEP_LAST" | "KEEP_ALL"
#   depth:       positive integer

ROS2_QOS_DEFAULT_PUBLISHER = {
    "reliability": "RELIABLE",
    "durability": "VOLATILE",
    "history": "KEEP_LAST",
    "depth": 10,
}

ROS2_QOS_DEFAULT_SUBSCRIPTION = {
    "reliability": "RELIABLE",
    "durability": "VOLATILE",
    "history": "KEEP_LAST",
    "depth": 10,
}

# Per-topic QoS overrides for ROS2 publishers (bridge publishing into ROS2).
ROS2_QOS_PUBLISHER_OVERRIDES = {
    # High-rate, loss-tolerant sensor-like data.
    "/wheel_odometry/odometry": {
        "reliability": "BEST_EFFORT",
        "durability": "VOLATILE",
        "history": "KEEP_LAST",
        "depth": 100,
    },
    "/tf": {
        "reliability": "BEST_EFFORT",
        "durability": "VOLATILE",
        "history": "KEEP_LAST",
        "depth": 100,
    },
    "/received_messages": {
        "reliability": "RELIABLE",
        "durability": "VOLATILE",
        "history": "KEEP_LAST",
        "depth": 100,
    },
    "/sent_messages": {
        "reliability": "BEST_EFFORT",
        "durability": "VOLATILE",
        "history": "KEEP_LAST",
        "depth": 100,
    },
}

# Per-topic QoS overrides for ROS2 subscriptions (bridge reading from ROS2).
ROS2_QOS_SUBSCRIPTION_OVERRIDES = {
    # Map should behave like a latched topic on ROS2 (TRANSIENT_LOCAL).
    "/map": {
        "reliability": "RELIABLE",
        "durability": "TRANSIENT_LOCAL",
        "history": "KEEP_LAST",
        "depth": 1,
    },
    "/received_messages": {
        "reliability": "BEST_EFFORT",
        "durability": "VOLATILE",
        "history": "KEEP_LAST",
        "depth": 100,
    },
    "/sent_messages": {
        "reliability": "BEST_EFFORT",
        "durability": "VOLATILE",
        "history": "KEEP_LAST",
        "depth": 100,
    },
}


# ------------------------- ROS1 \"QoS-like\" configuration --------------------
#
# ROS1 does not have QoS profiles, but we can still expose queue sizes and
# latching behavior as configuration. These are consumed in `ros1_handlers.py`.

ROS1_PUBLISHER_QUEUE_SIZE_DEFAULT = 1
ROS1_SUBSCRIBER_QUEUE_SIZE_DEFAULT = 10

# Optional per-topic overrides for ROS1 publishers (queue_size only).
ROS1_PUBLISHER_QUEUE_SIZE_OVERRIDES = {
    # Example:
    # "/map": 1,
}

# Optional per-topic overrides for ROS1 subscribers (queue_size only).
ROS1_SUBSCRIBER_QUEUE_SIZE_OVERRIDES = {
    # Example:
    # "/tf": 50,
}

