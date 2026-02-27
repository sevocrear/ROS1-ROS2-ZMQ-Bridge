"""
Runtime configuration helpers for the ROS1–ROS2 ZMQ bridge.

User-facing, persistent configuration such as topics, types, and QoS
profiles lives in `schema.py`.

This module contains only small runtime helpers and environment-driven
settings that are shared by the bridge components.
"""

from __future__ import annotations

import os
from typing import Optional


def env_int(name: str, default: int) -> int:
    """
    Read an integer from an environment variable with basic validation.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise SystemExit(f"Invalid integer for env var {name}={raw!r}")


def env_float(name: str, default: float) -> float:
    """
    Read a float from an environment variable with basic validation.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        raise SystemExit(f"Invalid float for env var {name}={raw!r}")


# --- ZMQ / queue configuration ------------------------------------------------

# Max items in each per-topic send queue.
SEND_QUEUE_MAXSIZE: int = env_int("BRIDGE_SEND_QUEUE_MAXSIZE", 100)

# ZMQ high-water mark for PUB/SUB sockets (per-socket buffer depth).
ZMQ_HWM: int = env_int("BRIDGE_ZMQ_HWM", 500)

# Seconds to wait after ZMQ connect for the slow-joiner handshake.
ZMQ_CONNECT_DELAY: float = env_float("BRIDGE_ZMQ_CONNECT_DELAY", 1.0)


# --- QoS discovery configuration (ROS2) ---------------------------------------

# Maximum time to wait for ROS2 graph discovery when trying to infer QoS
# from existing publishers/subscribers on a topic.
QOS_DISCOVERY_TIMEOUT_SEC: float = env_float(
    "BRIDGE_QOS_DISCOVERY_TIMEOUT_SEC",
    2.0,
)

# Poll interval while waiting for discovery to find endpoints.
QOS_DISCOVERY_POLL_INTERVAL_SEC: float = env_float(
    "BRIDGE_QOS_DISCOVERY_POLL_INTERVAL_SEC",
    0.1,
)

