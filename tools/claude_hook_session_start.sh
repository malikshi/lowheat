#!/usr/bin/env bash
# claude_hook_session_start.sh — Claude Code SessionStart hook for CodeDNA v0.9.
#
# Emits a session-start banner with project name and module count
# so the agent reads .codedna before editing source files.

set -euo pipefail

CODEDNA=".codedna"
if [[ ! -f "$CODEDNA" ]]; then
    exit 0
fi

pkgs=$(grep -c 'purpose:' "$CODEDNA" 2>/dev/null || echo 0)
proj=$(grep '^project:' "$CODEDNA" | head -1 | cut -d' ' -f2-)

cat <<EOF
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[CodeDNA] Project: $proj — $pkgs documented modules. Read .codedna, AGENTS.md, and CLAUDE.md before editing source files. Every source edit requires updating agent: with today's date."}}
EOF

# RTK reminder
if command -v rtk &>/dev/null; then
    echo '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[RTK] Prefer rtk-wrapped commands: rtk git status, rtk ls, rtk read <file>, rtk rg pattern. See RTK.md for full reference."}}'
fi
