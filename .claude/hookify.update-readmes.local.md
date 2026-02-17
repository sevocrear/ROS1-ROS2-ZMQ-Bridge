---
name: update-readmes-on-bridge-change
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: bridge/(schema|interfaces|ros[12]_serializer|ros[12]_handlers|ros[12]_relay)\.py$|docker/(Dockerfile\.bridge_ros[12])$|docker-compose\.yml$|tests/
---

**Bridge source code was modified — check if READMEs need updating.**

Two documentation files track the bridge architecture and must stay in sync with the code:

1. **`README.md`** (project root) — topics table, configuration env vars, behavior & performance notes, project layout tree.
2. **`bridge/README.md`** — topics table, file roles, data model & serialization, ZMQ & threading model, "adding a new topic" guide and checklist.

**What to check after this edit:**

- **Topic changes** (`schema.py`, handlers, serializers): update the topics table in both READMEs.
- **New/removed files**: update the "File roles" table in `bridge/README.md` and the project layout tree in root `README.md`.
- **Serialization changes** (serializers): update "Data model & serialization" in `bridge/README.md` and "Behavior & performance notes" in root `README.md`.
- **ZMQ / threading / queue changes** (relays, schema): update "ZMQ & threading model" in `bridge/README.md` and "Behavior & performance notes" in root `README.md`.
- **QoS changes** (`ros2_handlers.py`): update QoS notes in both READMEs and the topics table.
- **Environment variable changes** (`schema.py`, relays): update "Configuration" section in root `README.md` and relevant notes in `bridge/README.md`.
- **Docker changes** (Dockerfiles, docker-compose): update "Quick start" and "Project layout" in root `README.md`.
- **Test changes**: update test-related instructions if applicable.

Read both READMEs, compare with the code change you just made, and update any sections that are now stale. Do NOT skip this step.
