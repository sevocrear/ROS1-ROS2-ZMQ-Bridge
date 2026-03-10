#!/bin/bash
# =============================================================================
# PointCloud2 bridge test: publish from ROS1 /driver/lidar/top, verify on ROS2.
# Runs via docker exec. Copies test scripts into containers then runs them.
#
# Usage: ./tests/run_pointcloud_test.sh
#
# Requirements: docker compose up -d (roscore + bridge-ros1 + bridge-ros2)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROS1_CONTAINER="${ROS1_CONTAINER:-ros1_ros2_zmq_bridge-bridge-ros1-1}"
ROS2_CONTAINER="${ROS2_CONTAINER:-ros1_ros2_zmq_bridge-bridge-ros2-1}"
WARMUP="${WARMUP:-3}"
TIMEOUT="${TIMEOUT:-15}"

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
info() { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[PASS]${NC}  $*"; }
fail() { echo -e "${RED}[FAIL]${NC}  $*"; }

cleanup() {
    info "Stopping ROS1 pointcloud publisher ..."
    docker exec "$ROS1_CONTAINER" pkill -f "ros1_publish_pointcloud" 2>/dev/null || true
}
trap cleanup EXIT

info "Checking containers ..."
for c in "$ROS1_CONTAINER" "$ROS2_CONTAINER"; do
    if ! docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null | grep -q true; then
        fail "Container $c is not running. Start with: docker compose up -d"
        exit 1
    fi
done

info "Copying test scripts into containers ..."
docker cp "$SCRIPT_DIR/ros1_publish_pointcloud.py" "$ROS1_CONTAINER:/tmp/ros1_publish_pointcloud.py"
docker cp "$SCRIPT_DIR/ros2_check_pointcloud.py" "$ROS2_CONTAINER:/tmp/ros2_check_pointcloud.py"

info "Starting ROS1 PointCloud2 publisher on /driver/lidar/top ..."
docker exec -d "$ROS1_CONTAINER" bash -c "source /opt/ros/noetic/setup.bash && python3 /tmp/ros1_publish_pointcloud.py --topic /driver/lidar/top --rate 5 --frame lidar_top"

info "Warming up for ${WARMUP}s ..."
sleep "$WARMUP"

info "Running ROS2 checker (timeout ${TIMEOUT}s) ..."
if docker exec "$ROS2_CONTAINER" bash -c "source /opt/ros/kilted/setup.bash && python3 /tmp/ros2_check_pointcloud.py --topic /driver/lidar/top --min-messages 3 --expected-frame lidar_top --expected-data-len 36 --timeout $TIMEOUT"; then
    ok "PointCloud2 bridge test passed: messages bridged from ROS1 to ROS2."
    exit 0
else
    fail "PointCloud2 bridge test failed."
    exit 1
fi
