"""
Small JSON helpers used by the ROS1–ROS2 ZMQ bridge.

This keeps JSON handling separate from the user-facing configuration
in `schema.py`.
"""

from __future__ import annotations

import json
from typing import Any, Dict


def decode_message(body: bytes) -> Dict[str, Any]:
    """
    Decode a ZMQ message body (UTF‑8 encoded JSON) into a dict.
    """
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))

