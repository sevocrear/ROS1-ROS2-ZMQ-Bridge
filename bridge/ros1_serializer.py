"""
Serialize/deserialize between ROS1 messages and JSON dict (shared shape with ROS2).
Used only in ros1_relay (rospy). All imports at module level.
"""

import array as _array
import base64

from ackermann_msgs.msg import AckermannDriveStamped
from can_msgs.msg import Frame
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import OccupancyGrid, Odometry, Path
from tf2_msgs.msg import TFMessage

from schema import TOPIC_TO_TYPE


# --- AckermannDriveStamped ---

def ackermann_drive_stamped_to_dict(msg):
    """ROS1 AckermannDriveStamped -> dict (ROS2-compatible: stamp.sec, stamp.nanosec)."""
    return {
        "header": {
            "stamp": {"sec": msg.header.stamp.secs, "nanosec": msg.header.stamp.nsecs},
            "frame_id": msg.header.frame_id or "",
        },
        "drive": {
            "steering_angle": msg.drive.steering_angle,
            "steering_angle_velocity": msg.drive.steering_angle_velocity,
            "speed": msg.drive.speed,
            "acceleration": msg.drive.acceleration,
            "jerk": msg.drive.jerk,
        },
    }


def dict_to_ackermann_drive_stamped(d, msg_class):
    """Dict -> ROS1 AckermannDriveStamped."""
    msg = msg_class()
    h = d.get("header", {})
    stamp = h.get("stamp", {})
    msg.header.stamp.secs = stamp.get("secs", stamp.get("sec", 0))
    msg.header.stamp.nsecs = stamp.get("nsecs", stamp.get("nanosec", 0))
    msg.header.frame_id = h.get("frame_id", "")
    dr = d.get("drive", {})
    msg.drive.steering_angle = float(dr.get("steering_angle", 0))
    msg.drive.steering_angle_velocity = float(dr.get("steering_angle_velocity", 0))
    msg.drive.speed = float(dr.get("speed", 0))
    msg.drive.acceleration = float(dr.get("acceleration", 0))
    msg.drive.jerk = float(dr.get("jerk", 0))
    return msg


# --- PoseStamped ---

def pose_stamped_to_dict(msg):
    """ROS1 PoseStamped -> dict (sec/nanosec for bridge)."""
    return {
        "header": {
            "stamp": {"sec": msg.header.stamp.secs, "nanosec": msg.header.stamp.nsecs},
            "frame_id": msg.header.frame_id or "",
        },
        "pose": {
            "position": {"x": msg.pose.position.x, "y": msg.pose.position.y, "z": msg.pose.position.z},
            "orientation": {
                "x": msg.pose.orientation.x,
                "y": msg.pose.orientation.y,
                "z": msg.pose.orientation.z,
                "w": msg.pose.orientation.w,
            },
        },
    }


def dict_to_pose_stamped(d, msg_class):
    """Dict -> ROS1 PoseStamped."""
    msg = msg_class()
    h = d.get("header", {})
    stamp = h.get("stamp", {})
    msg.header.stamp.secs = stamp.get("secs", stamp.get("sec", 0))
    msg.header.stamp.nsecs = stamp.get("nsecs", stamp.get("nanosec", 0))
    msg.header.frame_id = h.get("frame_id", "")
    p = d.get("pose", {})
    pos = p.get("position", {})
    msg.pose.position.x = float(pos.get("x", 0))
    msg.pose.position.y = float(pos.get("y", 0))
    msg.pose.position.z = float(pos.get("z", 0))
    ori = p.get("orientation", {})
    msg.pose.orientation.x = float(ori.get("x", 0))
    msg.pose.orientation.y = float(ori.get("y", 0))
    msg.pose.orientation.z = float(ori.get("z", 0))
    msg.pose.orientation.w = float(ori.get("w", 1))
    return msg


# --- TransformStamped (single) ---

def transform_stamped_to_dict(msg):
    """ROS1 TransformStamped -> dict."""
    return {
        "header": {
            "stamp": {"sec": msg.header.stamp.secs, "nanosec": msg.header.stamp.nsecs},
            "frame_id": msg.header.frame_id or "",
        },
        "child_frame_id": msg.child_frame_id or "",
        "transform": {
            "translation": {"x": msg.transform.translation.x, "y": msg.transform.translation.y, "z": msg.transform.translation.z},
            "rotation": {
                "x": msg.transform.rotation.x,
                "y": msg.transform.rotation.y,
                "z": msg.transform.rotation.z,
                "w": msg.transform.rotation.w,
            },
        },
    }


def dict_to_transform_stamped(d, msg_class):
    """Dict -> ROS1 TransformStamped."""
    msg = msg_class()
    h = d.get("header", {})
    stamp = h.get("stamp", {})
    msg.header.stamp.secs = stamp.get("secs", stamp.get("sec", 0))
    msg.header.stamp.nsecs = stamp.get("nsecs", stamp.get("nanosec", 0))
    msg.header.frame_id = h.get("frame_id", "")
    msg.child_frame_id = d.get("child_frame_id", "")
    t = d.get("transform", {})
    trans = t.get("translation", {})
    msg.transform.translation.x = float(trans.get("x", 0))
    msg.transform.translation.y = float(trans.get("y", 0))
    msg.transform.translation.z = float(trans.get("z", 0))
    rot = t.get("rotation", {})
    msg.transform.rotation.x = float(rot.get("x", 0))
    msg.transform.rotation.y = float(rot.get("y", 0))
    msg.transform.rotation.z = float(rot.get("z", 0))
    msg.transform.rotation.w = float(rot.get("w", 1))
    return msg


# --- TFMessage ---

def tf_message_to_dict(msg):
    """ROS1 TFMessage -> dict (list of transforms)."""
    return {"transforms": [transform_stamped_to_dict(t) for t in msg.transforms]}


def dict_to_tf_message(d, msg_class):
    """Dict -> ROS1 TFMessage."""
    msg = msg_class()
    msg.transforms = [dict_to_transform_stamped(t, TransformStamped) for t in d.get("transforms", [])]
    return msg


# --- OccupancyGrid ---

def occupancy_grid_to_dict(msg):
    """ROS1 OccupancyGrid -> dict.  Data is base64-encoded (signed int8) for efficiency."""
    raw = _array.array('b', msg.data).tobytes()
    return {
        "header": {
            "stamp": {"sec": msg.header.stamp.secs, "nanosec": msg.header.stamp.nsecs},
            "frame_id": msg.header.frame_id or "",
        },
        "info": {
            "width": msg.info.width,
            "height": msg.info.height,
            "resolution": msg.info.resolution,
            "origin": {
                "position": {"x": msg.info.origin.position.x, "y": msg.info.origin.position.y, "z": msg.info.origin.position.z},
                "orientation": {
                    "x": msg.info.origin.orientation.x,
                    "y": msg.info.origin.orientation.y,
                    "z": msg.info.origin.orientation.z,
                    "w": msg.info.origin.orientation.w,
                },
            },
        },
        "data_b64": base64.b64encode(raw).decode("ascii"),
    }


def dict_to_occupancy_grid(d, msg_class):
    """Dict -> ROS1 OccupancyGrid.  Accepts base64 (data_b64) or legacy int-list (data)."""
    msg = msg_class()
    h = d.get("header", {})
    stamp = h.get("stamp", {})
    msg.header.stamp.secs = stamp.get("secs", stamp.get("sec", 0))
    msg.header.stamp.nsecs = stamp.get("nsecs", stamp.get("nanosec", 0))
    msg.header.frame_id = h.get("frame_id", "")
    info = d.get("info", {})
    msg.info.width = int(info.get("width", 0))
    msg.info.height = int(info.get("height", 0))
    msg.info.resolution = float(info.get("resolution", 0))
    orig = info.get("origin", {})
    pos = orig.get("position", {})
    msg.info.origin.position.x = float(pos.get("x", 0))
    msg.info.origin.position.y = float(pos.get("y", 0))
    msg.info.origin.position.z = float(pos.get("z", 0))
    ori = orig.get("orientation", {})
    msg.info.origin.orientation.x = float(ori.get("x", 0))
    msg.info.origin.orientation.y = float(ori.get("y", 0))
    msg.info.origin.orientation.z = float(ori.get("z", 0))
    msg.info.origin.orientation.w = float(ori.get("w", 1))
    if "data_b64" in d:
        raw = base64.b64decode(d["data_b64"])
        a = _array.array('b')
        a.frombytes(raw)
        msg.data = list(a)
    else:
        msg.data = list(d.get("data", []))
    return msg


# --- Odometry ---

def odometry_to_dict(msg):
    """ROS1 Odometry -> dict (ROS2-compatible: stamp.sec, stamp.nanosec)."""
    return {
        "header": {
            "stamp": {"sec": msg.header.stamp.secs, "nanosec": msg.header.stamp.nsecs},
            "frame_id": msg.header.frame_id or "",
        },
        "child_frame_id": msg.child_frame_id or "",
        "pose": {
            "pose": {
                "position": {"x": msg.pose.pose.position.x, "y": msg.pose.pose.position.y, "z": msg.pose.pose.position.z},
                "orientation": {
                    "x": msg.pose.pose.orientation.x,
                    "y": msg.pose.pose.orientation.y,
                    "z": msg.pose.pose.orientation.z,
                    "w": msg.pose.pose.orientation.w,
                },
            },
            "covariance": list(msg.pose.covariance),
        },
        "twist": {
            "twist": {
                "linear": {"x": msg.twist.twist.linear.x, "y": msg.twist.twist.linear.y, "z": msg.twist.twist.linear.z},
                "angular": {"x": msg.twist.twist.angular.x, "y": msg.twist.twist.angular.y, "z": msg.twist.twist.angular.z},
            },
            "covariance": list(msg.twist.covariance),
        },
    }


def dict_to_odometry(d, msg_class):
    """Dict -> ROS1 Odometry."""
    msg = msg_class()
    h = d.get("header", {})
    stamp = h.get("stamp", {})
    msg.header.stamp.secs = stamp.get("secs", stamp.get("sec", 0))
    msg.header.stamp.nsecs = stamp.get("nsecs", stamp.get("nanosec", 0))
    msg.header.frame_id = h.get("frame_id", "")
    msg.child_frame_id = d.get("child_frame_id", "")
    pose_block = d.get("pose", {})
    p = pose_block.get("pose", {})
    pos = p.get("position", {})
    msg.pose.pose.position.x = float(pos.get("x", 0))
    msg.pose.pose.position.y = float(pos.get("y", 0))
    msg.pose.pose.position.z = float(pos.get("z", 0))
    ori = p.get("orientation", {})
    msg.pose.pose.orientation.x = float(ori.get("x", 0))
    msg.pose.pose.orientation.y = float(ori.get("y", 0))
    msg.pose.pose.orientation.z = float(ori.get("z", 0))
    msg.pose.pose.orientation.w = float(ori.get("w", 1))
    cov = pose_block.get("covariance", [])
    for i in range(min(36, len(cov))):
        msg.pose.covariance[i] = float(cov[i])
    twist_block = d.get("twist", {})
    t = twist_block.get("twist", {})
    lin = t.get("linear", {})
    msg.twist.twist.linear.x = float(lin.get("x", 0))
    msg.twist.twist.linear.y = float(lin.get("y", 0))
    msg.twist.twist.linear.z = float(lin.get("z", 0))
    ang = t.get("angular", {})
    msg.twist.twist.angular.x = float(ang.get("x", 0))
    msg.twist.twist.angular.y = float(ang.get("y", 0))
    msg.twist.twist.angular.z = float(ang.get("z", 0))
    cov_t = twist_block.get("covariance", [])
    for i in range(min(36, len(cov_t))):
        msg.twist.covariance[i] = float(cov_t[i])
    return msg


# --- Path ---

def path_to_dict(msg):
    """ROS1 Path -> dict."""
    return {
        "header": {
            "stamp": {"sec": msg.header.stamp.secs, "nanosec": msg.header.stamp.nsecs},
            "frame_id": msg.header.frame_id or "",
        },
        "poses": [pose_stamped_to_dict(p) for p in msg.poses],
    }


def dict_to_path(d, msg_class):
    """Dict -> ROS1 Path."""
    msg = msg_class()
    h = d.get("header", {})
    stamp = h.get("stamp", {})
    msg.header.stamp.secs = stamp.get("secs", stamp.get("sec", 0))
    msg.header.stamp.nsecs = stamp.get("nsecs", stamp.get("nanosec", 0))
    msg.header.frame_id = h.get("frame_id", "")
    msg.poses = [dict_to_pose_stamped(p, PoseStamped) for p in d.get("poses", [])]
    return msg


# --- can_msgs/Frame ---

def frame_to_dict(msg):
    """ROS1 can_msgs/Frame -> dict (ROS2-compatible: stamp.sec, stamp.nanosec). data as ints for JSON."""
    return {
        "header": {
            "stamp": {"sec": msg.header.stamp.secs, "nanosec": msg.header.stamp.nsecs},
            "frame_id": msg.header.frame_id or "",
        },
        "id": int(msg.id),
        "is_rtr": bool(msg.is_rtr),
        "is_extended": bool(msg.is_extended),
        "is_error": bool(msg.is_error),
        "dlc": int(msg.dlc),
        "data": [int(x) for x in msg.data],
    }


def dict_to_frame(d, msg_class):
    """Dict -> ROS1 can_msgs/Frame. Assign data as a sequence; ROS1 msg.data can be bytes (immutable)."""
    msg = msg_class()
    h = d.get("header", {})
    stamp = h.get("stamp", {})
    msg.header.stamp.secs = stamp.get("secs", stamp.get("sec", 0))
    msg.header.stamp.nsecs = stamp.get("nsecs", stamp.get("nanosec", 0))
    msg.header.frame_id = h.get("frame_id", "")
    msg.id = int(d.get("id", 0))
    msg.is_rtr = bool(d.get("is_rtr", False))
    msg.is_extended = bool(d.get("is_extended", False))
    msg.is_error = bool(d.get("is_error", False))
    msg.dlc = int(d.get("dlc", 0))
    data_src = d.get("data", [])
    msg.data = [int(data_src[i]) & 0xFF if i < len(data_src) else 0 for i in range(8)]
    return msg


# --- Type-based dispatch (topic names come from schema.TOPIC_TO_TYPE) ---

# Message type string (ROS2 style, from schema) -> (msg_to_dict_fn, dict_to_msg_fn)
TYPE_TO_SERIALIZER = {
    "ackermann_msgs/msg/AckermannDriveStamped": (
        ackermann_drive_stamped_to_dict,
        dict_to_ackermann_drive_stamped,
    ),
    "geometry_msgs/msg/PoseStamped": (pose_stamped_to_dict, dict_to_pose_stamped),
    "nav_msgs/msg/Path": (path_to_dict, dict_to_path),
    "nav_msgs/msg/OccupancyGrid": (
        occupancy_grid_to_dict,
        dict_to_occupancy_grid,
    ),
    "can_msgs/msg/Frame": (frame_to_dict, dict_to_frame),
    "nav_msgs/msg/Odometry": (odometry_to_dict, dict_to_odometry),
    "tf2_msgs/msg/TFMessage": (tf_message_to_dict, dict_to_tf_message),
}


def serialize_ros1(topic: str, msg):
    """ROS1 message -> dict for given topic. Uses schema.TOPIC_TO_TYPE for dispatch."""
    msg_type = TOPIC_TO_TYPE.get(topic)
    if msg_type is None:
        raise KeyError(f"serialize_ros1: topic not in schema: {topic}")
    entry = TYPE_TO_SERIALIZER.get(msg_type)
    if entry is None:
        raise KeyError(f"serialize_ros1: type {msg_type} has no serializer")
    to_dict_fn, _ = entry
    return to_dict_fn(msg)


def deserialize_ros1(topic: str, d: dict, msg_class):
    """Dict -> ROS1 message for given topic. Uses schema.TOPIC_TO_TYPE for dispatch."""
    msg_type = TOPIC_TO_TYPE.get(topic)
    if msg_type is None:
        raise KeyError(f"deserialize_ros1: topic not in schema: {topic}")
    entry = TYPE_TO_SERIALIZER.get(msg_type)
    if entry is None:
        raise KeyError(f"deserialize_ros1: type {msg_type} has no deserializer")
    _, to_msg_fn = entry
    return to_msg_fn(d, msg_class)
