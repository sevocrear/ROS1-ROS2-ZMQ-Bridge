#!/bin/bash
# =============================================================================
# Bridge Hz test — publishes on one side, measures Hz on the other.
# Runs entirely via "docker exec" against the running compose stack.
#
# Usage:
#   ./tests/run_bridge_test.sh                  # default settings
#   WARMUP=8 MEASURE=15 ./tests/run_bridge_test.sh   # custom timing
#   TOLERANCE=0.40 ./tests/run_bridge_test.sh         # 40 % tolerance
#
# Requirements:
#   docker compose up -d   (roscore + bridge-ros1 + bridge-ros2 must be running)
# =============================================================================
set -euo pipefail

# --------------- configuration (override via env) ----------------------------
ROS1_CONTAINER="${ROS1_CONTAINER:-ros1_ros2_zmq_bridge-bridge-ros1-1}"
ROS2_CONTAINER="${ROS2_CONTAINER:-ros1_ros2_zmq_bridge-bridge-ros2-1}"

WARMUP="${WARMUP:-5}"         # seconds to let publishers settle before measuring
MEASURE="${MEASURE:-10}"      # seconds to collect Hz data
TOLERANCE="${TOLERANCE:-0.30}" # 30 % deviation allowed (0.30 = ±30 %)

# ANSI colours
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

# --------------- helpers -----------------------------------------------------
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[PASS]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }

PIDS_TO_KILL=()
cleanup() {
    info "Cleaning up background publishers …"
    for pid in "${PIDS_TO_KILL[@]}"; do
        kill "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
    done
    # Also kill any leftover pub processes inside containers
    docker exec "$ROS1_CONTAINER" bash -c 'pkill -f "rostopic pub" 2>/dev/null' || true
    docker exec "$ROS2_CONTAINER" bash -c 'pkill -f "ros2 topic pub" 2>/dev/null' || true
    info "Cleanup done."
}
trap cleanup EXIT

# --------------- preflight ---------------------------------------------------
info "Checking containers are running …"
for c in "$ROS1_CONTAINER" "$ROS2_CONTAINER"; do
    if ! docker inspect -f '{{.State.Running}}' "$c" 2>/dev/null | grep -q true; then
        fail "Container $c is not running. Start with: docker compose up -d"
        exit 1
    fi
done
info "Both containers are up."

# --------------- start publishers --------------------------------------------
info "Starting ROS1 publishers (inside $ROS1_CONTAINER) …"

# /tf at 100 Hz
docker exec -d "$ROS1_CONTAINER" bash -c '
source /opt/ros/noetic/setup.bash
rostopic pub /tf tf2_msgs/TFMessage "transforms:
- header:
    seq: 0
    stamp: {secs: 0, nsecs: 0}
    frame_id: \"base\"
  child_frame_id: \"child\"
  transform:
    translation: {x: 1.0, y: 2.0, z: 0.0}
    rotation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}" -r 100
'
info "  /tf at 100 Hz"

# /move_base_simple/goal at 10 Hz
docker exec -d "$ROS1_CONTAINER" bash -c '
source /opt/ros/noetic/setup.bash
rostopic pub /move_base_simple/goal geometry_msgs/PoseStamped "header:
  seq: 0
  stamp: {secs: 0, nsecs: 0}
  frame_id: \"map\"
pose:
  position: {x: 1.0, y: 2.0, z: 0.0}
  orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}" -r 10
'
info "  /move_base_simple/goal at 10 Hz"

info "Starting ROS2 publishers (inside $ROS2_CONTAINER) …"

# /control_cmd at 1000 Hz
docker exec -d "$ROS2_CONTAINER" bash -c '
source /opt/ros/kilted/setup.bash
ros2 topic pub /control_cmd ackermann_msgs/msg/AckermannDriveStamped -r 1000
'
info "  /control_cmd at 1000 Hz"

# /map at 100 Hz
docker exec -d "$ROS2_CONTAINER" bash -c '
source /opt/ros/kilted/setup.bash
ros2 topic pub /map nav_msgs/msg/OccupancyGrid --qos-durability transient_local -r 100
'
info "  /map at 100 Hz"

# --------------- warmup ------------------------------------------------------
info "Warming up for ${WARMUP}s …"
sleep "$WARMUP"

# --------------- measure Hz --------------------------------------------------
# Runs "rostopic hz" / "ros2 topic hz" for $MEASURE seconds, captures output,
# extracts the last "average rate:" line.
#
# Returns the float average rate, or "0" if nothing received.

measure_ros1_hz() {
    local topic="$1"
    local output
    output=$(docker exec "$ROS1_CONTAINER" bash -c "
        source /opt/ros/noetic/setup.bash
        timeout ${MEASURE} rostopic hz ${topic} 2>&1
    " 2>&1 || true)
    # rostopic hz format:  "average rate: 99.123"
    local rate
    rate=$(echo "$output" | grep 'average rate' | tail -1 | awk '{print $3}')
    echo "${rate:-0}"
}

measure_ros2_hz() {
    local topic="$1"
    local output
    output=$(docker exec "$ROS2_CONTAINER" bash -c "
        source /opt/ros/kilted/setup.bash
        export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
        timeout ${MEASURE} ros2 topic hz ${topic} 2>&1
    " 2>&1 || true)
    # ros2 topic hz format:  "average rate: 99.123"
    local rate
    rate=$(echo "$output" | grep 'average rate' | tail -1 | awk -F: '{print $2}' | tr -d ' ')
    echo "${rate:-0}"
}

# Check whether measured_hz is within TOLERANCE of expected_hz.
# Returns 0 (pass) or 1 (fail).
check_hz() {
    local label="$1"
    local expected="$2"
    local measured="$3"

    if [ "$measured" = "0" ] || [ -z "$measured" ]; then
        fail "$label — expected ~${expected} Hz, got NO MESSAGES"
        return 1
    fi

    local ok_flag
    ok_flag=$(awk "BEGIN {
        lo = ${expected} * (1 - ${TOLERANCE});
        hi = ${expected} * (1 + ${TOLERANCE});
        print (${measured} >= lo && ${measured} <= hi) ? 1 : 0
    }")

    if [ "$ok_flag" = "1" ]; then
        ok "$label — expected ~${expected} Hz, measured ${measured} Hz"
        return 0
    else
        fail "$label — expected ~${expected} Hz (±${TOLERANCE}), measured ${measured} Hz"
        return 1
    fi
}

# --------------- run measurements --------------------------------------------
FAILURES=0

echo ""
info "===== ROS1 → ROS2 (measuring on ROS2 side) ====="

info "Measuring /tf on ROS2 …"
hz_tf=$(measure_ros2_hz /tf)
check_hz "ROS2 /tf" 100 "$hz_tf" || ((FAILURES++)) || true

info "Measuring /move_base_simple/goal on ROS2 …"
hz_goal=$(measure_ros2_hz /move_base_simple/goal)
check_hz "ROS2 /move_base_simple/goal" 10 "$hz_goal" || ((FAILURES++)) || true

echo ""
info "===== ROS2 → ROS1 (measuring on ROS1 side) ====="

info "Measuring /control_cmd on ROS1 …"
hz_cmd=$(measure_ros1_hz /control_cmd)
check_hz "ROS1 /control_cmd" 1000 "$hz_cmd" || ((FAILURES++)) || true

info "Measuring /map on ROS1 …"
hz_map=$(measure_ros1_hz /map)
check_hz "ROS1 /map" 100 "$hz_map" || ((FAILURES++)) || true

# --------------- summary -----------------------------------------------------
echo ""
echo "========================================"
echo "  RESULTS"
echo "========================================"
echo "  /tf             (ROS1→ROS2): ${hz_tf} Hz  (expected ~100)"
echo "  /move_base_simple/goal (ROS1→ROS2): ${hz_goal} Hz  (expected ~10)"
echo "  /control_cmd    (ROS2→ROS1): ${hz_cmd} Hz  (expected ~1000)"
echo "  /map            (ROS2→ROS1): ${hz_map} Hz  (expected ~100)"
echo "========================================"

if [ "$FAILURES" -gt 0 ]; then
    echo ""
    fail "${FAILURES} test(s) failed (tolerance: ±$(awk "BEGIN{printf \"%.0f\", ${TOLERANCE}*100}")%)"
    exit 1
else
    echo ""
    ok "All tests passed (tolerance: ±$(awk "BEGIN{printf \"%.0f\", ${TOLERANCE}*100}")%)"
    exit 0
fi
