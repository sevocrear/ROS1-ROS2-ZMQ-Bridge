# Bridge Hz tests

Simple end-to-end test that publishes topics on one side and checks the received
Hz on the other side — all via `docker exec` against the running compose stack.

## What it tests

| Published from | Topic | Rate | Checked on |
|---|---|---|---|
| ROS1 | `/tf` | 100 Hz | ROS2 |
| ROS1 | `/move_base_simple/goal` | 10 Hz | ROS2 |
| ROS1 | `/driver/lidar/top` (PointCloud2) | 5 Hz | ROS2 (see below) |
| ROS2 | `/control_cmd` | 1000 Hz | ROS1 |
| ROS2 | `/map` | 100 Hz | ROS1 |

### PointCloud2 bridge test

A dedicated script verifies that `sensor_msgs/PointCloud2` is correctly bridged from ROS1 to ROS2 for `/driver/lidar/top`:

```bash
./tests/run_pointcloud_test.sh
```

This starts a synthetic PointCloud2 publisher in the ROS1 container and checks on the ROS2 side that messages arrive with the expected `frame_id` and data length. No need to run `run_bridge_test.sh` for this; run it anytime the bridge is up.

## Usage

```bash
# 1. Make sure the bridge stack is running
docker compose up -d

# 2. Run the test (from repo root)
./tests/run_bridge_test.sh
```

### Configuration (env vars)

| Variable | Default | Description |
|---|---|---|
| `WARMUP` | `5` | Seconds to wait after starting publishers |
| `MEASURE` | `10` | Seconds to collect Hz data |
| `TOLERANCE` | `0.30` | Allowed deviation (0.30 = ±30%) |
| `ROS1_CONTAINER` | `ros1_ros2_zmq_bridge-bridge-ros1-1` | ROS1 container name |
| `ROS2_CONTAINER` | `ros1_ros2_zmq_bridge-bridge-ros2-1` | ROS2 container name |

### Examples

```bash
# Longer measurement, tighter tolerance
WARMUP=10 MEASURE=20 TOLERANCE=0.20 ./tests/run_bridge_test.sh

# Different container names
ROS1_CONTAINER=my-ros1 ROS2_CONTAINER=my-ros2 ./tests/run_bridge_test.sh
```

## Cleanup

The script kills all `rostopic pub` / `ros2 topic pub` processes inside the
containers on exit (including on Ctrl+C).
