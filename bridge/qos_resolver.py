"""
QoS resolution helpers for the ROS2 side of the bridge.

This module turns the static, user-editable QoS configuration from
`schema.py` into concrete `QoSProfile` instances and, when possible,
merges them with QoS discovered from existing publishers/subscribers
on the ROS2 graph.
"""

from __future__ import annotations

import time
from typing import Dict, Iterable, List

from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    HistoryPolicy,
    QoSProfile,
    ReliabilityPolicy,
)

from config_utils import (
    QOS_DISCOVERY_POLL_INTERVAL_SEC,
    QOS_DISCOVERY_TIMEOUT_SEC,
)
from schema import (
    ROS2_QOS_DEFAULT_PUBLISHER,
    ROS2_QOS_DEFAULT_SUBSCRIPTION,
    ROS2_QOS_PUBLISHER_OVERRIDES,
    ROS2_QOS_SUBSCRIPTION_OVERRIDES,
)


_RELIABILITY_MAP: Dict[str, ReliabilityPolicy] = {
    "RELIABLE": ReliabilityPolicy.RELIABLE,
    "BEST_EFFORT": ReliabilityPolicy.BEST_EFFORT,
}

_DURABILITY_MAP: Dict[str, DurabilityPolicy] = {
    "VOLATILE": DurabilityPolicy.VOLATILE,
    "TRANSIENT_LOCAL": DurabilityPolicy.TRANSIENT_LOCAL,
}

_HISTORY_MAP: Dict[str, HistoryPolicy] = {
    "KEEP_LAST": HistoryPolicy.KEEP_LAST,
    "KEEP_ALL": HistoryPolicy.KEEP_ALL,
}


def _qos_from_config(config: Dict[str, object]) -> QoSProfile:
    """
    Build a QoSProfile from a simple dict.
    """
    reliability_str = str(config.get("reliability", "RELIABLE")).upper()
    durability_str = str(config.get("durability", "VOLATILE")).upper()
    history_str = str(config.get("history", "KEEP_LAST")).upper()
    depth_val = config.get("depth", 10)

    reliability = _RELIABILITY_MAP.get(reliability_str, ReliabilityPolicy.RELIABLE)
    durability = _DURABILITY_MAP.get(durability_str, DurabilityPolicy.VOLATILE)
    history = _HISTORY_MAP.get(history_str, HistoryPolicy.KEEP_LAST)

    depth = 10
    if isinstance(depth_val, int) and depth_val > 0:
        depth = depth_val

    return QoSProfile(
        depth=depth,
        reliability=reliability,
        durability=durability,
        history=history,
    )


_DEFAULT_PUBLISHER_QOS = _qos_from_config(ROS2_QOS_DEFAULT_PUBLISHER)
_DEFAULT_SUBSCRIPTION_QOS = _qos_from_config(ROS2_QOS_DEFAULT_SUBSCRIPTION)


def _merge_profiles(profiles: Iterable[QoSProfile], default_profile: QoSProfile) -> QoSProfile:
    """
    Merge multiple endpoint QoS profiles into a single profile that is
    compatible with all of them as much as possible.
    """
    reliability = default_profile.reliability
    durability = default_profile.durability
    history = default_profile.history
    depth = default_profile.depth

    any_profile = False
    for p in profiles:
        any_profile = True
        # Reliability: prefer RELIABLE if any endpoint requires it.
        if p.reliability == ReliabilityPolicy.RELIABLE:
            reliability = ReliabilityPolicy.RELIABLE
        elif reliability != ReliabilityPolicy.RELIABLE:
            reliability = p.reliability

        # Durability: prefer TRANSIENT_LOCAL if any endpoint requires it.
        if p.durability == DurabilityPolicy.TRANSIENT_LOCAL:
            durability = DurabilityPolicy.TRANSIENT_LOCAL
        elif durability != DurabilityPolicy.TRANSIENT_LOCAL:
            durability = p.durability

        # History: prefer KEEP_ALL if any endpoint uses it.
        if p.history == HistoryPolicy.KEEP_ALL:
            history = HistoryPolicy.KEEP_ALL
        elif history != HistoryPolicy.KEEP_ALL:
            history = p.history

        # Depth: take the maximum non-zero depth.
        if p.depth and p.depth > depth:
            depth = p.depth

    if not any_profile:
        return default_profile

    return QoSProfile(
        depth=depth,
        reliability=reliability,
        durability=durability,
        history=history,
    )


def _wait_for_endpoints(func, topic: str):
    """
    Poll the ROS2 graph via the given function until endpoints are found
    or the configured timeout elapses.
    """
    deadline = time.monotonic() + QOS_DISCOVERY_TIMEOUT_SEC
    endpoints = func(topic)
    while not endpoints and time.monotonic() < deadline:
        time.sleep(QOS_DISCOVERY_POLL_INTERVAL_SEC)
        endpoints = func(topic)
    return endpoints


def resolve_subscription_qos(node: Node, topic: str) -> QoSProfile:
    """
    Resolve QoS for a ROS2 subscription (bridge reading from ROS2).

    Precedence:
    1. Per-topic override from schema.ROS2_QOS_SUBSCRIPTION_OVERRIDES.
    2. Merge QoS from existing publishers on the topic.
    3. Global default from schema.ROS2_QOS_DEFAULT_SUBSCRIPTION.
    """
    override = ROS2_QOS_SUBSCRIPTION_OVERRIDES.get(topic)
    if override is not None:
        merged_conf: Dict[str, object] = dict(ROS2_QOS_DEFAULT_SUBSCRIPTION)
        merged_conf.update(override)
        return _qos_from_config(merged_conf)

    try:
        infos = _wait_for_endpoints(node.get_publishers_info_by_topic, topic)
    except Exception:
        # If introspection fails for any reason, fall back to defaults.
        infos = []

    if infos:
        profiles: List[QoSProfile] = [info.qos_profile for info in infos]
        return _merge_profiles(profiles, _DEFAULT_SUBSCRIPTION_QOS)

    return _DEFAULT_SUBSCRIPTION_QOS


def resolve_publisher_qos(node: Node, topic: str) -> QoSProfile:
    """
    Resolve QoS for a ROS2 publisher (bridge publishing into ROS2).

    Precedence:
    1. Per-topic override from schema.ROS2_QOS_PUBLISHER_OVERRIDES.
    2. Merge QoS from existing subscriptions on the topic.
    3. Global default from schema.ROS2_QOS_DEFAULT_PUBLISHER.
    """
    override = ROS2_QOS_PUBLISHER_OVERRIDES.get(topic)
    if override is not None:
        merged_conf: Dict[str, object] = dict(ROS2_QOS_DEFAULT_PUBLISHER)
        merged_conf.update(override)
        return _qos_from_config(merged_conf)

    try:
        infos = _wait_for_endpoints(node.get_subscriptions_info_by_topic, topic)
    except Exception:
        infos = []

    if infos:
        profiles: List[QoSProfile] = [info.qos_profile for info in infos]
        return _merge_profiles(profiles, _DEFAULT_PUBLISHER_QOS)

    return _DEFAULT_PUBLISHER_QOS

