#!/bin/bash
# Cursor stop hook: checks if bridge source files were modified but READMEs
# were not updated. If so, sends a followup_message asking the agent to
# update both README.md and bridge/README.md.
#
# Input (JSON on stdin):
#   { "status": "completed"|"aborted"|"error", "loop_count": N, ... }
#
# Output (JSON on stdout):
#   { "followup_message": "..." }   — to continue the session
#   {}                               — to allow normal stop

set -euo pipefail

input=$(cat)

# Only check on the first stop attempt to avoid infinite loops.
loop_count=$(echo "$input" | python3 -c "import sys,json; print(json.load(sys.stdin).get('loop_count', 0))" 2>/dev/null || echo "0")
if [ "$loop_count" -gt 0 ]; then
  echo '{}'
  exit 0
fi

# Patterns for bridge source files (the ones that affect documentation).
BRIDGE_SRC_PATTERN='bridge/(schema|interfaces|ros[12]_serializer|ros[12]_handlers|ros[12]_relay)\.py$|docker/(Dockerfile\.bridge_ros[12])$|docker-compose\.yml$|tests/'

# Patterns for the two READMEs.
README_ROOT='README\.md$'
README_BRIDGE='bridge/README\.md$'

cd "${CURSOR_PROJECT_DIR:-.}"

# Get list of modified/added files (staged + unstaged + untracked).
changed_files=$(git diff --name-only HEAD 2>/dev/null; git diff --name-only --cached 2>/dev/null; git ls-files --others --exclude-standard 2>/dev/null) || true

if [ -z "$changed_files" ]; then
  echo '{}'
  exit 0
fi

# Deduplicate
changed_files=$(echo "$changed_files" | sort -u)

# Check if any bridge source file was modified.
bridge_changed=$(echo "$changed_files" | grep -E "$BRIDGE_SRC_PATTERN" || true)

if [ -z "$bridge_changed" ]; then
  # No bridge source files touched — nothing to remind about.
  echo '{}'
  exit 0
fi

# Check which READMEs were already updated.
root_readme_ok=$(echo "$changed_files" | grep -E "^$README_ROOT" || true)
bridge_readme_ok=$(echo "$changed_files" | grep -E "^$README_BRIDGE" || true)

missing_readmes=""
if [ -z "$root_readme_ok" ]; then
  missing_readmes="README.md (project root)"
fi
if [ -z "$bridge_readme_ok" ]; then
  if [ -n "$missing_readmes" ]; then
    missing_readmes="$missing_readmes and bridge/README.md"
  else
    missing_readmes="bridge/README.md"
  fi
fi

if [ -z "$missing_readmes" ]; then
  # Both READMEs were updated — all good.
  echo '{}'
  exit 0
fi

# Build the list of changed bridge files for context.
file_list=$(echo "$bridge_changed" | head -10 | sed 's/^/  - /')

cat <<EOF
{
  "followup_message": "Bridge source files were modified but $missing_readmes was not updated. Please review and update the stale README(s) to reflect the changes in:\n$file_list\n\nCheck: topic table, file roles, serialization notes, ZMQ/threading model, QoS notes, env vars, Docker notes, and project layout as applicable."
}
EOF
