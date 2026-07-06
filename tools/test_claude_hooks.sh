#!/usr/bin/env bash
# test_claude_hooks.sh — focused regression tests for Claude hook behavior.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local label="$3"

    if [[ "$haystack" != *"$needle"* ]]; then
        printf 'FAIL: %s\nExpected to find: %s\nActual output:\n%s\n' "$label" "$needle" "$haystack"
        exit 1
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local label="$3"

    if [[ "$haystack" == *"$needle"* ]]; then
        printf 'FAIL: %s\nDid not expect to find: %s\nActual output:\n%s\n' "$label" "$needle" "$haystack"
        exit 1
    fi
}

run_session_start_mentions_agents_contract() {
    local output
    output="$(cd "$REPO_ROOT" && bash tools/claude_hook_session_start.sh)"

    assert_contains "$output" 'AGENTS.md' 'SessionStart hook should point agents at the main contract'
    assert_contains "$output" 'CLAUDE.md' 'SessionStart hook should still mention the Claude adapter'
}

run_pretooluse_accepts_stdin_payload() {
    local output
    output="$(cd "$REPO_ROOT" && printf '{"file_path":"manager/src/config.py"}' | bash tools/claude_hook_pretooluse.sh)"

    assert_contains "$output" '[CodeDNA] Source file.' 'PreToolUse hook should read stdin JSON payloads'
}

run_stop_hook_blocks_untracked_project_files() {
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' RETURN

    cp "$REPO_ROOT/tools/claude_hook_stop.sh" "$tmp_dir/claude_hook_stop.sh"
    (
        cd "$tmp_dir"
        git init -q
        git config user.email test@example.invalid
        git config user.name 'Hook Test'
        printf 'project: hook-test\nmode: semi\n\nagent_sessions:\n' > .codedna
        git add .codedna claude_hook_stop.sh
        git commit -qm 'initial manifest'
        printf 'new tracked candidate\n' > new_file.txt

        local output
        output="$(bash claude_hook_stop.sh)"

        assert_contains "$output" '"decision": "block"' 'Stop hook should block untracked project files'
        assert_contains "$output" 'new_file.txt' 'Stop hook block output should name untracked project files'
    )
}

run_stop_hook_ignores_untracked_skill_files() {
    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' RETURN

    cp "$REPO_ROOT/tools/claude_hook_stop.sh" "$tmp_dir/claude_hook_stop.sh"
    (
        cd "$tmp_dir"
        git init -q
        git config user.email test@example.invalid
        git config user.name 'Hook Test'
        mkdir -p .agents/skills/example
        printf 'project: hook-test\nmode: semi\n\nagent_sessions:\n' > .codedna
        git add .codedna claude_hook_stop.sh
        git commit -qm 'initial manifest'
        printf 'skill scratch\n' > .agents/skills/example/SKILL.md

        local output
        output="$(bash claude_hook_stop.sh)"

        assert_not_contains "$output" '"decision": "block"' 'Stop hook should ignore untracked installed skill files'
        assert_contains "$output" 'Session ledger check passed' 'Stop hook should pass when only ignored untracked files changed'
    )
}

run_session_start_mentions_agents_contract
run_pretooluse_accepts_stdin_payload
run_stop_hook_blocks_untracked_project_files
run_stop_hook_ignores_untracked_skill_files

printf 'Claude hook tests passed\n'
