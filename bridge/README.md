# Bridge code (ROS1–ROS2 ZMQ)

This directory contains the Python bridge logic. See the [main README](../README.md) for why this package exists and how to run it with Docker.

## Topics (out of the box)

| Topic          | Direction   | Type                                   | Notes     |
|----------------|-------------|----------------------------------------|-----------|
| `/tf`          | ROS1 → ROS2 | tf2_msgs/msg/TFMessage                 | High rate |
| `/goal_pose`   | ROS1 → ROS2 | geometry_msgs/msg/PoseStamped          |           |
| `/map`         | ROS2 → ROS1 | nav_msgs/msg/OccupancyGrid             | Latched   |
| `/control_cmd` | ROS2 → ROS1 | ackermann_msgs/msg/AckermannDriveStamped |          |
| `/plan`        | ROS2 → ROS1 | nav_msgs/msg/Path                      |           |

## File roles

| File                | Role |
|---------------------|------|
| **schema.py**       | Topic ↔ type name, direction sets, `LATCHED_TOPICS`, JSON encode/decode. |
| **interfaces.py**   | Abstract `ROS1Publisher`, `ROS1Subscriber`, `ROS2Publisher`, `ROS2Subscriber`. |
| **ros1_serializer.py** | ROS1 message ↔ dict; `serialize_ros1()`, `deserialize_ros1()`. |
| **ros2_serializer.py** | ROS2 message ↔ dict; `serialize_ros2()`, `deserialize_ros2()`. |
| **ros1_handlers.py**   | Concrete ROS1 handlers; `create_ros1_publishers()`, `create_ros1_subscribers()`. |
| **ros2_handlers.py**   | Concrete ROS2 handlers; QoS (e.g. TRANSIENT_LOCAL for `/map`). |
| **ros1_relay.py**   | ZMQ bind, handlers, receive loop + rospy.spin. |
| **ros2_relay.py**   | ZMQ connect, handlers, receive loop + rclpy.spin. |
| **bridge.yaml**     | Reference config (topics, QoS). |

## Adding a new topic

Use the same dict shape on both sides (ROS1: `secs`/`nsecs`, ROS2: `sec`/`nanosec`; serializers normalize).

### New topic: **ROS1 → ROS2**

Example: `/my_topic` with type `std_msgs/String`.

1. **schema.py**: Add to `TOPIC_TO_TYPE` and to `ROS1_TO_ROS2_TOPICS`.
2. **ros1_serializer.py**: Import message type; add `*_to_dict` / `dict_to_*`; extend `serialize_ros1()` and `deserialize_ros1()`.
3. **ros2_serializer.py**: Same dict shape; extend `serialize_ros2()` and `deserialize_ros2()`.
4. **ros1_handlers.py**: Add topic → message class in `TOPIC_TO_ROS1_MSG`.
5. **ros2_handlers.py**: Add topic → message class in `TOPIC_TO_ROS2_MSG`; set QoS in `register()` if needed.
6. From repo root: `docker compose build` and `docker compose up -d`.

### New topic: **ROS2 → ROS1**

Same steps; add to `ROS2_TO_ROS1_TOPICS` in schema. If latched, add to `LATCHED_TOPICS` and set TRANSIENT_LOCAL QoS for that topic in `ros2_handlers.py`.

### Checklist

- [ ] **schema.py**: `TOPIC_TO_TYPE`, direction set, and `LATCHED_TOPICS` if latched.
- [ ] **ros1_serializer.py**: Message class, serialize/deserialize, and branches in `serialize_ros1()` / `deserialize_ros1()`.
- [ ] **ros2_serializer.py**: Same; branches in `serialize_ros2()` / `deserialize_ros2()`.
- [ ] **ros1_handlers.py**: Topic in `TOPIC_TO_ROS1_MSG`.
- [ ] **ros2_handlers.py**: Topic in `TOPIC_TO_ROS2_MSG`; QoS if needed.
- [ ] Rebuild both images and restart.

## Dependencies

- **pyzmq** in the container. ROS packages (rospy, rclpy, ackermann_msgs, nav_msgs, geometry_msgs, tf2_msgs) come from the system ROS in each Docker image.
