#!/usr/bin/env bash
# claude_hook_codedna.sh — Claude Code PostToolUse hook for CodeDNA v0.9 enforcement.
#
# Receives JSON on stdin from Claude Code with tool_name, tool_input, tool_output.
# Validates that Python/TS/Go/etc files have a CodeDNA v0.9 header after Write or Edit.
#
# Exit 0 = OK (feedback shown to agent)
# Exit 2 = block (prevents the tool action — only for PreToolUse, not PostToolUse)

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "$(pwd)")"
VALIDATOR="$REPO_ROOT/tools/validate_manifests.py"

# Read CodeDNA mode from .codedna (default: semi)
CODEDNA_MODE=$(grep '^mode:' "$REPO_ROOT/.codedna" 2>/dev/null | head -1 | awk '{print $2}' || echo "semi")

# Read JSON from stdin
INPUT=$(cat)

# Extract file_path from tool_input
FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
data = json.load(sys.stdin)
inp = data.get('tool_input', {})
print(inp.get('file_path', ''))
" 2>/dev/null || echo "")

# No file path — nothing to check
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only check source files
if ! echo "$FILE_PATH" | grep -qE '\.(py|ts|tsx|js|jsx|go|rs|java|kt|swift|rb|cs|php)$'; then
    exit 0
fi

if [[ "$FILE_PATH" == "$REPO_ROOT/"* ]]; then
    REL_PATH="${FILE_PATH#"$REPO_ROOT"/}"
else
    REL_PATH="${FILE_PATH#./}"
fi

# Intentional validation boundary.
#
# Compatibility: CodeDNA headers describe stable module contracts. Package
# marker files, pytest fixtures, installed agent skills, bootstrap/runtime
# config, migration output, experiment run artifacts, vendored dependencies,
# and virtual environments either have no stable contract or are not
# project-authored source. Requiring headers there creates noisy session-stop
# failures without improving source navigation.
#
# Safety: this PostToolUse hook is advisory. The installed pre-commit hook still
# validates staged project source before commit, so a missed interactive warning
# does not silently enter history.
#
# Tested: `codedna install --path /home/malik/sing-box --tools claude agents
# --no-wiki-sync`, `.git/hooks/pre-commit`, and `git diff --check` were run
# during setup on 2026-05-21.
BASENAME=$(basename "$FILE_PATH")
if [[ "$BASENAME" == "__init__.py" ]] || \
   [[ "$BASENAME" == "conftest.py" ]] || \
   [[ "$REL_PATH" == .agents/skills/* ]] || \
   [[ "$REL_PATH" == .claude/skills/* ]] || \
   [[ "$REL_PATH" == .codex/* ]] || \
   [[ "$FILE_PATH" == *"/migrations/"* ]] || \
   [[ "$FILE_PATH" == *"/experiments/runs/"* ]] || \
   [[ "$FILE_PATH" == *"/node_modules/"* ]] || \
   [[ "$FILE_PATH" == *"/venv/"* ]] || \
   [[ "$FILE_PATH" == *"/.venv/"* ]]; then
    exit 0
fi

# Check if validator exists
if [[ ! -f "$VALIDATOR" ]]; then
    echo "⚠ CodeDNA: validate_manifests.py not found — skipping check"
    exit 0
fi

# Run validation
OUTPUT=$(python3 "$VALIDATOR" "$FILE_PATH" 2>&1) || true

if echo "$OUTPUT" | grep -q "^FAIL "; then
    echo ""
    echo "File: $FILE_PATH"
    if echo "$OUTPUT" | grep -q "Missing L2 Rules"; then
        echo "━━━ CodeDNA v0.9 — L2 function annotations ━━━"
        echo "$OUTPUT" | grep -E "Missing L2 Rules" | head -10 | sed 's/^/  /'
        echo ""
        echo "Add Rules: to public function docstrings before commit."
    else
        ERRORS=$(echo "$OUTPUT" | grep -E "error:|missing:" | head -5)
        echo "━━━ CodeDNA v0.9 — annotation missing or incomplete ━━━"
        echo "$ERRORS" | sed 's/^/  /'
        echo ""
        echo "Required header (Python):"
        echo '  """filename.py — purpose ≤15 words.'
        echo ""
        echo "  exports: function(arg) -> type"
        echo "  used_by: caller.py → caller_fn"
        echo "  rules:   constraint"
        echo '  agent:   model-id | YYYY-MM-DD | what you did'
        echo '  """'
    fi
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    # Exit 0 — PostToolUse can't block, but feedback goes to the agent
    exit 0
fi

# L2 check: public functions without Rules: docstring (Python only)
# In human mode, skip L2 enforcement (only critical functions need Rules:)
if [[ "$CODEDNA_MODE" == "human" ]]; then
    exit 0
fi
if [[ "$FILE_PATH" == *.py ]]; then
    L2_ISSUES=$(python3 -c "
import ast, sys
try:
    with open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
        tree = ast.parse(f.read())
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith('_'):
                continue
            doc = ast.get_docstring(node) or ''
            if 'Rules:' not in doc:
                print(f'  L2: {node.name}() (line {node.lineno}) — missing Rules: docstring')
except Exception:
    pass
" "$FILE_PATH" 2>/dev/null || true)

    if [[ -n "$L2_ISSUES" ]]; then
        echo ""
        echo "━━━ CodeDNA v0.9 — L2 function annotations ━━━"
        echo "File: $FILE_PATH"
        echo "$L2_ISSUES"
        echo ""
        echo "Add Rules: and message: to public function docstrings:"
        echo '  def my_function():'
        echo '      """Short description.'
        echo ''
        echo '      Rules:   constraint the agent must respect'
        echo '      message: model-id | YYYY-MM-DD | observation for next agent'
        echo '      """'
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    fi
fi

# Reminder: if logic was changed, consider updating rules: and message:
if echo "$FILE_PATH" | grep -qE '\.(py|ts|tsx|js|go|rs|java|kt|php|rb|cs|swift)$'; then
    echo ""
    if [[ "$CODEDNA_MODE" == "agent" ]]; then
        echo "[CodeDNA:agent] You MUST:"
        echo "  - Update rules: in the module header if you discovered a new constraint"
        echo "  - Add message: if you noticed something the next agent should verify"
        echo "  - Add # Rules: or # message: inline above all non-trivial logic blocks"
        echo "  - Rename ambiguous variables to type_shape_domain_origin convention"
    else
        echo "[CodeDNA:$CODEDNA_MODE] If you changed business logic, constraints, or edge cases:"
        echo "  - Update rules: in the module header if you discovered a new constraint"
        echo "  - Add message: if you noticed something the next agent should verify"
    fi
fi

exit 0
