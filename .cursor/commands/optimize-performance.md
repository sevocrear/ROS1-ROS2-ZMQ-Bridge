# Deep Performance & Safety Audit

## Overview

Perform a thorough audit of the entire codebase for **performance bottlenecks**, **concurrency bugs**, **memory issues**, and **reliability problems**. This is a ROS1/ROS2 ZMQ bridge — pay special attention to multi-threaded message passing, ZMQ socket lifecycle, serialization overhead, and Docker networking. Every finding must reference **specific files and line numbers**.

## Instructions

Before starting, **read and understand the full project structure** — every `.py` file under `bridge/`, Dockerfiles under `docker/`, `docker-compose.yml`, and `bridge/bridge.yaml`.

Work through **all** sections below in order. For each finding, provide:

1. **File and line** where the issue lives.
2. **Severity**: Critical / High / Medium / Low.
3. **What the problem is** (concrete, not vague).
4. **Concrete fix** — show the corrected code or the approach.
5. **Estimated impact** — what improves and by roughly how much.

---

## 1. Data Races & Concurrency Issues

- [ ] Identify **shared mutable state** accessed by multiple threads/callbacks without synchronization (e.g., ROS callbacks + ZMQ send/recv on the same data).
- [ ] Check for **race conditions** between ROS subscriber callbacks and ZMQ publisher threads.
- [ ] Verify that ZMQ sockets are **not shared across threads** (ZMQ sockets are not thread-safe).
- [ ] Look for **callback queue contention** — ROS1 spinners vs. manual thread management.
- [ ] Check for **missing locks or atomic operations** on counters, flags, or shared buffers.
- [ ] Inspect whether `rospy.Rate` / `rclpy` executors are correctly scoped to their thread.
- [ ] Look for **TOCTOU (time-of-check-to-time-of-use)** bugs in any conditional logic involving shared state.

## 2. Memory Leaks & Resource Management

- [ ] Find **unbounded queues or buffers** — messages piling up if the consumer is slower than the producer.
- [ ] Check for **ZMQ socket leaks** — sockets opened but never closed on error paths or shutdown.
- [ ] Look for **ROS publisher/subscriber leaks** — handles created in loops or conditionally without cleanup.
- [ ] Detect **large message retention** — e.g., latched `/map` messages kept in memory longer than necessary, or copies accumulating.
- [ ] Verify proper **context manager / `finally` cleanup** for ZMQ contexts, sockets, and ROS nodes.
- [ ] Check for **circular references** or closures that prevent garbage collection.
- [ ] Identify any **growing data structures** (lists, dicts) that are appended to but never pruned.

## 3. Serialization & Deserialization Overhead

- [ ] Profile the JSON serialization path — are there **unnecessary deep copies** or intermediate representations?
- [ ] Check if large messages (e.g., `/map` OccupancyGrid, `/tf` at high rate) are being **serialized inefficiently** (e.g., Python lists of ints vs. base64-encoded bytes).
- [ ] Look for **repeated serialization** of the same message if it's sent to multiple destinations.
- [ ] Evaluate whether **msgpack, CBOR, or protobuf** would be significantly faster than JSON for high-rate topics.
- [ ] Check for **unnecessary string↔dict↔object conversions** in the serialization chain.

## 4. ZMQ Transport & Networking

- [ ] Verify **ZMQ socket types** (PUB/SUB) are appropriate — check for message loss on slow subscribers.
- [ ] Check for **missing HWM (High Water Mark)** settings that could cause unbounded memory growth or silent message drops.
- [ ] Look for **blocking send/recv calls** that could stall the relay loop.
- [ ] Verify **socket reconnection** handling — what happens when the peer goes down and comes back?
- [ ] Check if **ZMQ Poller** is used for efficient multiplexing or if busy-waiting is happening instead.
- [ ] Inspect TCP keepalive and linger settings — does the bridge hang on shutdown?
- [ ] Verify that topic filtering via ZMQ subscription prefixes is efficient.

## 5. ROS1 / ROS2 Specific Issues

- [ ] Check **ROS1 callback queue sizes** — are subscribers dropping messages silently?
- [ ] Verify **ROS2 QoS profiles** match what the bridge expects (reliability, durability, history depth).
- [ ] Look for **spin-blocking** issues — `rospy.spin()` or `rclpy.spin()` preventing graceful shutdown or health checks.
- [ ] Check if **ROS timers or Rate objects** are used efficiently or if busy-loops exist.
- [ ] Inspect `/tf` bridging — at high rates, is there batching or is each transform sent individually?
- [ ] Verify latched topic behavior — is `/map` re-published correctly on new subscriber connection?
- [ ] Check for **parameter / config reload** without restart support.

## 6. CPU & Algorithmic Bottlenecks

- [ ] Identify **hot loops** — any `while True` with no sleep or yield.
- [ ] Look for **O(n²) or worse** patterns in message handling (e.g., scanning all topics per message).
- [ ] Check for **excessive logging** at high-rate topics that could flood stdout/disk.
- [ ] Verify that **list comprehensions / generators** are preferred over manual loops where applicable.
- [ ] Look for **redundant operations** — decoding + re-encoding, duplicate lookups, etc.

## 7. Docker & Infrastructure

- [ ] Check Docker networking — is `host` network mode used where bridge mode would add unnecessary overhead (or vice versa)?
- [ ] Verify that containers have **appropriate resource limits** (memory, CPU).
- [ ] Look for **unnecessary layers or large images** in Dockerfiles.
- [ ] Check if logs are being captured and rotated properly, or if they fill up disk.
- [ ] Verify health checks and restart policies in `docker-compose.yml`.

## 8. Error Handling & Resilience

- [ ] Find **bare `except` clauses** that swallow errors silently.
- [ ] Check for **missing error handling** on ZMQ send/recv that could crash the relay.
- [ ] Verify behavior under **network partition** — does the bridge recover automatically?
- [ ] Look for **unhandled edge cases** in serialization (e.g., NaN, Inf, empty arrays, None values).
- [ ] Check **shutdown signal handling** — SIGTERM/SIGINT properly closing sockets and nodes.
- [ ] Verify **timeout handling** on all blocking operations.

## 9. Configuration & Deployment

- [ ] Check for **hardcoded values** that should be configurable (ports, rates, buffer sizes).
- [ ] Verify environment variable handling — what happens with missing or malformed values?
- [ ] Look for **security issues** — ZMQ sockets open to 0.0.0.0 without authentication.

---

## Output Format

After completing the audit, provide:

### Summary Table

| # | Category | File:Line | Severity | Issue (one-liner) | Fix Approach |
|---|----------|-----------|----------|--------------------|--------------|
| 1 | ...      | ...       | ...      | ...                | ...          |

### Detailed Findings

For each issue in the table, expand with:
- **Problem**: Detailed description with code snippet.
- **Impact**: What can go wrong (message loss, crash, OOM, data corruption, etc.).
- **Fix**: Corrected code or design change.
- **Estimated Improvement**: Quantitative if possible (e.g., "reduces `/tf` latency from ~5ms to ~1ms").

### Priority Action Plan

List the **top 5 fixes** ordered by impact-to-effort ratio, with implementation instructions.
