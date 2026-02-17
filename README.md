# ROS1–ROS2 ZMQ Bridge

A **custom bridge** between **ROS 1 (Noetic)** and **ROS 2 (Kilted)** using **ZMQ** and JSON serialization.  
It runs as two Docker services (ROS1 relay + ROS2 relay) that exchange messages over TCP.

---

## Why this package exists

We needed to run **ROS 2 Kilted** (Ubuntu 24.04) together with **ROS 1 Noetic** in the same system.  
The official [**ros1_bridge**](https://github.com/ros2/ros1_bridge) does **not** support ROS 2 Kilted: it targets older ROS 2 distros and, as stated in its [compatibility table](https://github.com/ros2/ros1_bridge#supported-ros-and-ubuntu-versions), **Ubuntu 24.04 (Noble) is not supported** for the bridge.

This package is a lightweight alternative:

- **ROS 1** relay (Ubuntu 20.04, Noetic) and **ROS 2** relay (Ubuntu 24.04, Kilted) run in separate containers.
- They communicate over **ZMQ** (TCP, configurable ports). Messages are serialized to a **shared JSON** format.
- Topic mapping and message shape are defined centrally in `bridge/schema.py` and the serializers.
- The code is designed to be **small, explicit and easy to extend** for new topics.

---

## Supported topics (out of the box)

Current topic mapping is driven by `bridge/schema.py`:

| Topic                         | Direction     | Type                                   | Notes                            |
|------------------------------|---------------|----------------------------------------|----------------------------------|
| `/tf`                        | ROS1 → ROS2   | `tf2_msgs/msg/TFMessage`              | High rate, BEST_EFFORT on ROS2  |
| `/move_base_simple/goal`     | ROS1 → ROS2   | `geometry_msgs/msg/PoseStamped`       | Navigation goal pose            |
| `/wheel_odometry/odometry`   | ROS1 → ROS2   | `nav_msgs/msg/Odometry`               | High rate, BEST_EFFORT on ROS2  |
| `/map`                       | ROS2 → ROS1   | `nav_msgs/msg/OccupancyGrid`          | Latched / TRANSIENT_LOCAL       |
| `/control_cmd`               | ROS2 → ROS1   | `ackermann_msgs/msg/AckermannDriveStamped` | Vehicle control             |
| `/move_base/PathPlanner/plan`| ROS2 → ROS1   | `nav_msgs/msg/Path`                   | Planned path                    |

The package currently supports this **limited set of topics**. It is intended to be **maintained and expanded by the community**: adding a new topic is a matter of editing the schema and the ROS1/ROS2 serializers (see `bridge/README.md` for details).

**Stars and pull requests are very much appreciated**—if this package is useful to you, consider starring the repo or contributing support for more topics or message types.

---

## Quick start

**Requirements:** Docker and Docker Compose.

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/ros1_ros2_zmq_bridge.git
cd ros1_ros2_zmq_bridge

# Build both bridge images
docker compose build

# Start roscore + bridge-ros1 + bridge-ros2
docker compose up -d
```

- `roscore` runs a standard Noetic roscore container (host networking).
- **bridge-ros1** binds ZMQ port **5555** (PUB, ros1→ros2) and **5556** (SUB, ros2→ros1). It needs a running ROS 1 master; point it with `ROS_MASTER_URI` (default: `http://localhost:11311`).
- **bridge-ros2** connects to bridge-ros1 at `BRIDGE_PEER_HOST` (default `127.0.0.1`) on 5555/5556.

Override ports with:

- `BRIDGE_ZMQ_PORT_ROS1_TO_ROS2` (default `5555`)
- `BRIDGE_ZMQ_PORT_ROS2_TO_ROS1` (default `5556`)

The Docker images are based on **ros-base** only (no desktop UI or navigation stacks) to keep them small.

---

## Configuration

Most behavior is controlled via environment variables (see `bridge/schema.py` and the relay scripts):

- **ZMQ ports**
  - `BRIDGE_ZMQ_PORT_ROS1_TO_ROS2` (int, default `5555`)
  - `BRIDGE_ZMQ_PORT_ROS2_TO_ROS1` (int, default `5556`)
- **ZMQ high-water mark / buffering**
  - `BRIDGE_ZMQ_HWM` (int, default `500`): per-socket ZMQ high-water mark for PUB/SUB.  
    Higher values buffer more messages (more RAM, fewer drops); lower values drop earlier under load.
- **Bridge send queue sizing**
  - `BRIDGE_SEND_QUEUE_MAXSIZE` (int, default `100`): internal Python queue capacity per direction.
- **ZMQ slow-joiner delay**
  - `BRIDGE_ZMQ_CONNECT_DELAY` (float seconds, default `1.0`): delay after connect to allow SUB/PUB handshakes before sending.
- **ROS master / peer**
  - `ROS_MASTER_URI` (for ROS1 containers; default `http://localhost:11311`)
  - `BRIDGE_PEER_HOST` (for ROS2 relay; default `127.0.0.1`)

All integer environment variables are validated at startup; invalid values cause a clear error and exit.

---

## Behavior & performance notes

- **Serialization**
  - All messages are serialized to a shared JSON-compatible dict shape.
  - `OccupancyGrid.data` is sent as a **base64-encoded int8 byte array** (not a giant JSON list of ints), which drastically **reduces memory usage and serialization time** for large maps.
- **ZMQ and queues**
  - Each relay uses **per-topic send queues** with a shared `threading.Event` for wake-up.  
    Each topic gets its own bounded buffer so a high-rate topic (e.g. `/tf` at 1 kHz) cannot starve or drop messages from a low-rate topic (e.g. `/map` at 0.1 Hz). The sender thread sleeps with zero CPU until a message arrives.
  - ZMQ sockets use `LINGER` and explicit close/`context.term()` for fast, clean shutdown.
- **QoS**
  - On the ROS2 side:
    - `/tf` and `/wheel_odometry/odometry` use **BEST_EFFORT** QoS (sensor-style, high-rate, loss-tolerant).
    - `/map` uses **RELIABLE + TRANSIENT_LOCAL** (latched behavior).
    - Other topics use **RELIABLE** QoS.


---

## Project layout

```text
.
├── README.md                 # This file
├── LICENSE                   # Apache-2.0
├── docker-compose.yml        # roscore + bridge-ros1 + bridge-ros2
├── docker/
│   ├── Dockerfile.bridge_ros1   # Ubuntu 20.04, ROS Noetic (ros-base)
│   └── Dockerfile.bridge_ros2   # Ubuntu 24.04, ROS 2 Kilted (ros-base)
├── bridge/                   # Python bridge code
│   ├── README.md             # How to add topics, file roles
│   ├── schema.py             # Topic ↔ type, directions, latched, ZMQ config
│   ├── interfaces.py         # Abstract publisher/subscriber interfaces
│   ├── ros1_serializer.py    # ROS1 message ↔ dict
│   ├── ros2_serializer.py    # ROS2 message ↔ dict
│   ├── ros1_handlers.py      # Concrete ROS1 handlers
│   ├── ros2_handlers.py      # Concrete ROS2 handlers
│   ├── ros1_relay.py         # ROS1 relay entrypoint
│   └── ros2_relay.py         # ROS2 relay entrypoint
└── tests/                    # End-to-end Hz / drop tests
    ├── README.md
    ├── docker-compose.test.yml
    ├── run_tests.sh
    ├── ros1_hz_checker.py
    ├── ros1_publisher.py
    ├── ros2_hz_checker.py
    └── ros2_publisher.py
```

---

## License

Apache-2.0. See [LICENSE](LICENSE).

---

## Related

- [ros1_bridge](https://github.com/ros2/ros1_bridge) — Official ROS 1 ↔ ROS 2 bridge (does not support ROS 2 Kilted on Ubuntu 24.04).
