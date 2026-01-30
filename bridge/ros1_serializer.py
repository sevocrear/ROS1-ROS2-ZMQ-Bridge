"""
Serialize/deserialize between ROS1 messages and JSON dict (shared shape with ROS2).
Used only in ros1_relay (rospy). All imports at module level.
"""

from ackermann_msgs.msg import AckermannDriveStamped
from geometry_msgs.msg import PoseStamped, TransformStamped
from nav_msgs.msg import OccupancyGrid, Path
from tf2_msgs.msg import TFMessage


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
    """ROS1 OccupancyGrid -> dict."""
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
        "data": list(msg.data),
    }


def dict_to_occupancy_grid(d, msg_class):
    """Dict -> ROS1 OccupancyGrid."""
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
    msg.data = list(d.get("data", []))
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


# --- Topic dispatch ---

def serialize_ros1(topic, msg):
    """ROS1 message -> dict for given topic. Raises KeyError if topic not supported."""
    if topic == "/control_cmd":
        return ackermann_drive_stamped_to_dict(msg)
    if topic == "/goal_pose":
        return pose_stamped_to_dict(msg)
    if topic == "/tf":
        return tf_message_to_dict(msg)
    if topic == "/map":
        return occupancy_grid_to_dict(msg)
    if topic == "/plan":
        return path_to_dict(msg)
    raise KeyError(f"serialize_ros1: unsupported topic {topic}")


def deserialize_ros1(topic, d, msg_class):
    """Dict -> ROS1 message for given topic."""
    if topic == "/control_cmd":
        return dict_to_ackermann_drive_stamped(d, msg_class)
    if topic == "/goal_pose":
        return dict_to_pose_stamped(d, msg_class)
    if topic == "/tf":
        return dict_to_tf_message(d, msg_class)
    if topic == "/map":
        return dict_to_occupancy_grid(d, msg_class)
    if topic == "/plan":
        return dict_to_path(d, msg_class)
    raise KeyError(f"deserialize_ros1: unsupported topic {topic}")
