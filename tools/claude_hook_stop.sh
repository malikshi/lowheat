#!/usr/bin/env bash
# claude_hook_stop.sh — Claude Code Stop hook for CodeDNA v0.9 session end protocol.
#
# Blocks session completion until .codedna has a session entry when tracked
# project files were modified during the session.

set -euo pipefail

mapfile -t CHANGED_FILES < <(
    {
        git diff --name-only HEAD 2>/dev/null || true
        git diff --cached --name-only 2>/dev/null || true
        git ls-files --others --exclude-standard 2>/dev/null || true
    } | sort -u | grep -vE '^$|^\.codedna$|^\.git/|^\.omx/|^\.codex/|^\.claude/skills/|^\.agents/skills/' || true
)

CODEDNA_SESSION_ADDED=false
EXPECTED_SESSION="${CLAUDE_SESSION_ID:-}"
if [[ -n "$EXPECTED_SESSION" ]]; then
    SESSION_MATCH="^\\+\\s+-\\s+session_id:.*${EXPECTED_SESSION}"
else
    SESSION_MATCH="^\\+\\s+-\\s+session_id:"
fi
if {
    git diff -- .codedna 2>/dev/null || true
    git diff --cached -- .codedna 2>/dev/null || true
} | grep -qE "$SESSION_MATCH"; then
    CODEDNA_SESSION_ADDED=true
fi

if [[ ${#CHANGED_FILES[@]} -gt 0 ]] && [[ "$CODEDNA_SESSION_ADDED" != true ]]; then
    FILE_LIST=$(printf '  - %s\n' "${CHANGED_FILES[@]}" | head -20)
    MESSAGE=$(cat <<EOF
CodeDNA v0.9 session ledger is required before stopping.

Tracked project files changed, but .codedna does not include a new session entry:
$FILE_LIST

Append an agent_sessions entry to .codedna with:
- agent
- provider
- date
- session_id
- task
- changed
- visited
- message

Then rerun the final response.
EOF
)
    MESSAGE="$MESSAGE" python3 -c 'import json, os; msg=os.environ["MESSAGE"]; print(json.dumps({"decision":"block","reason":msg,"systemMessage":msg}))'
    exit 0
fi

echo '{"systemMessage": "[CodeDNA] Session ledger check passed. If project files changed, .codedna includes a new session_id entry."}'

# RTK savings summary
if command -v rtk &>/dev/null; then
    rtk gain --session 2>/dev/null || true
fi

exit 0
