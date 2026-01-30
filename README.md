# ROS1–ROS2 ZMQ Bridge

A **custom bridge** between **ROS 1 (Noetic)** and **ROS 2 (Kilted)** using **ZMQ** and JSON serialization. Runs as two Docker services: a ROS1 relay and a ROS2 relay, exchanging messages over TCP.

---

## Why this package exists

We needed to run **ROS 2 Kilted** (e.g. on Ubuntu 24.04) together with **ROS 1 Noetic** in the same system. The official [**ros1_bridge**](https://github.com/ros2/ros1_bridge) does **not** support ROS 2 Kilted: it targets older ROS 2 distros and, as stated in its [compatibility table](https://github.com/ros2/ros1_bridge#supported-ros-and-ubuntu-versions), **Ubuntu 24.04 (Noble) is not supported** for the bridge. So we implemented this lightweight alternative:

- **ROS 1** relay (Ubuntu 20.04, Noetic) and **ROS 2** relay (Ubuntu 24.04, Kilted) run in separate containers.
- They communicate over **ZMQ** (TCP, configurable ports). Messages are serialized to a **shared JSON** format.
- You choose which topics to bridge by editing the schema and serializers; the design is modular and easy to extend.

---

## Supported topics (out of the box)

| Topic          | Direction   | Type                                   | Notes     |
|----------------|-------------|----------------------------------------|-----------|
| `/tf`          | ROS1 → ROS2 | tf2_msgs/msg/TFMessage                 | High rate |
| `/goal_pose`   | ROS1 → ROS2 | geometry_msgs/msg/PoseStamped          |           |
| `/map`         | ROS2 → ROS1 | nav_msgs/msg/OccupancyGrid             | Latched   |
| `/control_cmd` | ROS2 → ROS1 | ackermann_msgs/msg/AckermannDriveStamped |          |
| `/plan`        | ROS2 → ROS1 | nav_msgs/msg/Path                      |           |

The package currently supports this **limited set of topics**. It is intended to be **maintained and expanded by the community**: adding a new topic is a matter of editing the schema and the ROS1/ROS2 serializers (see [bridge/README.md](bridge/README.md)).

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

- **bridge-ros1** binds ZMQ port **5555** (PUB, ros1→ros2) and **5556** (SUB, ros2→ros1). It needs a running ROS 1 master; point it with `ROS_MASTER_URI` (default: `http://localhost:11311`).
- **bridge-ros2** connects to bridge-ros1 at `BRIDGE_PEER_HOST` (default `127.0.0.1`) on 5555/5556.

Override ports with `BRIDGE_ZMQ_PORT_ROS1_TO_ROS2` and `BRIDGE_ZMQ_PORT_ROS2_TO_ROS1`.

---

## Project layout

```
.
├── README.md                 # This file
├── LICENSE                   # Apache-2.0
├── docker-compose.yml        # roscore + bridge-ros1 + bridge-ros2
├── docker/
│   ├── Dockerfile.bridge_ros1   # Ubuntu 20.04, ROS Noetic
│   └── Dockerfile.bridge_ros2   # Ubuntu 24.04, ROS 2 Kilted
└── bridge/                   # Python bridge code
    ├── README.md             # How to add topics, file roles
    ├── schema.py             # Topic ↔ type, directions, latched
    ├── interfaces.py         # Abstract publisher/subscriber interfaces
    ├── ros1_serializer.py    # ROS1 message ↔ dict
    ├── ros2_serializer.py    # ROS2 message ↔ dict
    ├── ros1_handlers.py      # Concrete ROS1 handlers
    ├── ros2_handlers.py     # Concrete ROS2 handlers
    ├── ros1_relay.py         # ROS1 relay entrypoint
    ├── ros2_relay.py        # ROS2 relay entrypoint
    └── bridge.yaml          # Reference config (topics, QoS)
```

---

## License

Apache-2.0. See [LICENSE](LICENSE).

---

## Related

- [ros1_bridge](https://github.com/ros2/ros1_bridge) — Official ROS 1 ↔ ROS 2 bridge (does not support ROS 2 Kilted on Ubuntu 24.04).
