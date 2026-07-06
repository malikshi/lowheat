#!/usr/bin/env bash
# claude_hook_pretooluse.sh — Claude Code PreToolUse hook for CodeDNA v0.9.
#
# Checks if the file being edited is a source file and emits a reminder
# to read the docstring and verify CodeDNA annotations before editing.

set -euo pipefail

payload="${TOOL_INPUT:-}"
if [[ -z "$payload" ]] && [[ ! -t 0 ]]; then
    payload="$(cat)"
fi

f=$(printf '%s' "$payload" | python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)

tool_input = data.get("tool_input") if isinstance(data, dict) else None
if not isinstance(tool_input, dict):
    tool_input = data if isinstance(data, dict) else {}

print(tool_input.get("file_path") or tool_input.get("path") or "")
' 2>/dev/null || true)

if [[ -z "$f" ]]; then
    exit 0
fi

if echo "$f" | grep -qE '\.(py|ts|tsx|js|go|rs|java|kt|swift|rb|cs|php)$'; then
    cat <<'EOF'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[CodeDNA] Source file. Before editing: (1) read the docstring, (2) verify exports/used_by/rules/agent, (3) plan agent: update with the current session."}}
EOF
fi
