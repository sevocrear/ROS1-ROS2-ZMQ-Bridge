# Bridge code (ROS1–ROS2 ZMQ)

This directory contains the Python bridge logic that connects ROS1 and ROS2 via ZMQ.  
See the [main README](../README.md) for high-level overview, Docker usage and testing.

---

## Topics (out of the box)

This is the source of truth for the bridge behavior; it must stay in sync with `schema.py`.

| Topic                         | Direction     | Type                                   | Notes                                        |
|------------------------------|---------------|----------------------------------------|----------------------------------------------|
| `/tf`                        | ROS1 → ROS2   | `tf2_msgs/msg/TFMessage`              | High rate, BEST_EFFORT QoS on ROS2          |
| `/move_base_simple/goal`     | ROS1 → ROS2   | `geometry_msgs/msg/PoseStamped`       | Navigation goal pose                        |
| `/wheel_odometry/odometry`   | ROS1 → ROS2   | `nav_msgs/msg/Odometry`               | High rate, BEST_EFFORT QoS on ROS2          |
| `/map`                       | ROS2 → ROS1   | `nav_msgs/msg/OccupancyGrid`          | Latched / TRANSIENT_LOCAL on ROS2           |
| `/control_cmd`               | ROS2 → ROS1   | `ackermann_msgs/msg/AckermannDriveStamped` | Vehicle control commands               |
| `/move_base/PathPlanner/plan`| ROS2 → ROS1   | `nav_msgs/msg/Path`                   | Planned path                                |

All topic/type mappings and directions live in `schema.py` (`TOPIC_TO_TYPE`, `ROS1_TO_ROS2_TOPICS`, `ROS2_TO_ROS1_TOPICS`).

---

## File roles

| File                  | Role |
|-----------------------|------|
| `schema.py`           | Topic ↔ type mapping, direction sets, `LATCHED_TOPICS`, JSON decode, and ZMQ-related config (`SEND_QUEUE_MAXSIZE`, `ZMQ_HWM`, `ZMQ_CONNECT_DELAY`). |
| `interfaces.py`       | Abstract `ROS1Publisher`, `ROS1Subscriber`, `ROS2Publisher`, `ROS2Subscriber` interfaces shared by relays. |
| `ros1_serializer.py`  | ROS1 message ↔ dict; `serialize_ros1()`, `deserialize_ros1()`. Includes optimized `OccupancyGrid` serialization (base64 `data_b64`). |
| `ros2_serializer.py`  | ROS2 message ↔ dict; `serialize_ros2()`, `deserialize_ros2()`. Same dict shape as ROS1 side (including `data_b64` for maps). |
| `ros1_handlers.py`    | Concrete ROS1 handlers; builds `ROS1Publisher` / `ROS1Subscriber` from schema mapping and serializers. |
| `ros2_handlers.py`    | Concrete ROS2 handlers; builds `ROS2Publisher` / `ROS2Subscriber`, sets QoS profiles (e.g. BEST_EFFORT for `/tf`, TRANSIENT_LOCAL for `/map`). |
| `ros1_relay.py`       | ROS1 relay entrypoint: binds ZMQ PUB/SUB, owns per-topic send queues + shared wake event, runs ZMQ receive loop + `rospy.spin()`. |
| `ros2_relay.py`       | ROS2 relay entrypoint: connects ZMQ PUB/SUB, owns per-topic send queues + shared wake event, uses a guard condition + queue for thread-safe publishing, runs ZMQ receive loop + `rclpy.spin()`. |

There is no `bridge.yaml` currently used by the code; the schema is Python-only and lives in `schema.py`.

---

## Data model & serialization

- Both sides use a **shared dict shape** for each message type.
- Time fields are normalized:
  - ROS1: `header.stamp.secs` / `header.stamp.nsecs`
  - ROS2: `header.stamp.sec` / `header.stamp.nanosec`
  - The dict uses `{ "stamp": { "sec": ..., "nanosec": ... } }`, and serializers handle either flavor.
- `OccupancyGrid.data`:
  - Serialized as a base64-encoded signed int8 byte array under key `data_b64`.
  - Deserializers accept both `data_b64` (new, efficient format) and legacy `data` (JSON list of ints) for compatibility.

When adding a new type, mirror the same dict structure in both serializers.

---

## ZMQ & threading model

- Each relay creates:
  - One ZMQ **PUB** socket.
  - One ZMQ **SUB** socket.
  - **Per-topic send queues** (`queue.Queue` per topic, each bounded to `SEND_QUEUE_MAXSIZE`) so a high-rate topic cannot starve or drop messages from a low-rate topic.
  - A shared `threading.Event` that wakes the sender thread instantly when any callback enqueues a message — **no busy-wait loop**.
  - A background sender thread that round-robins all per-topic queues on each wake-up, calling `send_multipart()` for each pending item.
- ZMQ high-water marks (HWM) and delays:
  - `ZMQ_HWM` (from `schema.py`) sets `SNDHWM` / `RCVHWM` for all sockets.
  - `ZMQ_CONNECT_DELAY` adds a small sleep after ROS2 connects to give ZMQ SUB/PUB time to establish (slow-joiner).
- Shutdown:
  - Both relays explicitly close sockets and terminate the ZMQ context.
  - `LINGER` is set so shutdown is fast and does not block indefinitely on pending messages.

On the ROS2 side (`ros2_relay.py`), incoming ZMQ messages are pushed into a queue and a **guard condition** wakes the rclpy executor; publishing to ROS2 topics always happens from the executor thread (no cross‑thread `publish()` calls).

---

## Adding a new topic

Use the **same dict shape** on both sides. The serializers normalize ROS1 vs ROS2 time fields and minor layout differences.

### New topic: **ROS1 → ROS2**

Example: `/my_topic` with type `std_msgs/String`.

1. **`schema.py`**  
   - Add to `TOPIC_TO_TYPE` with ROS2-style type string, e.g.:
     - `"/my_topic": "std_msgs/msg/String"`.
   - Add topic name to `ROS1_TO_ROS2_TOPICS`.
2. **`ros1_serializer.py`**  
   - Import the ROS1 message type.
   - Implement `*_to_dict()` / `dict_to_*()` for that type.
   - Register functions in `TYPE_TO_SERIALIZER`, and ensure `serialize_ros1()` / `deserialize_ros1()` can dispatch to them via `TOPIC_TO_TYPE`.
3. **`ros2_serializer.py`**  
   - Import the ROS2 message type.
   - Implement the same dict shape as ROS1 side.
   - Register in `TYPE_TO_SERIALIZER` and ensure `serialize_ros2()` / `deserialize_ros2()` handle it.
4. **`ros1_handlers.py`**  
   - Add topic → ROS1 message class in `TYPE_TO_ROS1_MSG` / `TOPIC_TO_ROS1_MSG`.
5. **`ros2_handlers.py`**  
   - Add topic → ROS2 message class in `TYPE_TO_ROS2_MSG` / `TOPIC_TO_ROS2_MSG`.
   - Choose QoS in the helper(s): `_default_qos()`, `_sensor_qos()`, `_map_qos()`, or a new helper for your use case.
6. Rebuild and restart:
   - `docker compose build`
   - `docker compose up -d`

### New topic: **ROS2 → ROS1**

Same steps, but:

1. Add the topic to `ROS2_TO_ROS1_TOPICS` in `schema.py`.
2. If the topic should be latched (e.g. `OccupancyGrid`, static map):
   - Add it to `LATCHED_TOPICS`.
   - In `ros2_handlers.py`, use a QoS with `DurabilityPolicy.TRANSIENT_LOCAL`.
   - In `ros1_handlers.py`, create the ROS1 publisher with `latch=True`.

### Checklist

- [ ] **`schema.py`**: `TOPIC_TO_TYPE`, direction set (`ROS1_TO_ROS2_TOPICS` or `ROS2_TO_ROS1_TOPICS`), and `LATCHED_TOPICS` if latched.
- [ ] **`ros1_serializer.py`**: Message class import and serialize/deserialize helpers; registered in `TYPE_TO_SERIALIZER`.
- [ ] **`ros2_serializer.py`**: Same dict shape and registration in `TYPE_TO_SERIALIZER`.
- [ ] **`ros1_handlers.py`**: Topic present in `TYPE_TO_ROS1_MSG` / `TOPIC_TO_ROS1_MSG`.
- [ ] **`ros2_handlers.py`**: Topic present in `TYPE_TO_ROS2_MSG` / `TOPIC_TO_ROS2_MSG`, with correct QoS.
- [ ] Docker images rebuilt, containers restarted; optional: tests updated to cover the new topic.

---

## Dependencies

- **pyzmq** is installed in both bridge containers and used directly by the relays.
- ROS packages (`rospy`, `rclpy`, `ackermann_msgs`, `nav_msgs`, `geometry_msgs`, `tf2_msgs`, etc.) come from the system ROS installation inside each Docker image (Noetic / Kilted).
