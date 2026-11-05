# Harness support

Verified on 2026-10-31 against the binaries installed on the build host. Detection
is advisory; a green row means the installer emitted the paths, not that a live
session authenticated and loaded them. Installer changes after that date are
covered by the test suite and CI, not by a live harness session.

Node `24.22.1` is installed at `/opt/node-v24.22.1` and linked from
`/usr/local/bin`; the Debian `/usr/bin/node` `24.21.0` remains as a fallback.

| Harness | Tier | Global surface | Project surface | Binary / status |
|---|---|---|---|---|
| Claude Code | native | `~/.claude/{AGENTS,CLAUDE}.md`, companions, `skills/agents-contract` | `AGENTS.md`, `CLAUDE.md`, companions | installed; headless smoke timed out |
| Codex | native | `~/.codex/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions | `0.166.0`; headless smoke timed out |
| Command Code | native | `~/.commandcode/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions | installed; smoke returned `2026-10-31` |
| Grok | native | `~/.grok/AGENTS.md`, `~/.grok/rules/*.md`, `skills/agents-contract` | `AGENTS.md`, `.grok/rules/*.md` | installed; smoke returned `2026-10-31` |
| OpenCode | native | `~/.config/opencode/AGENTS.md`, companions | `AGENTS.md`, companions | installed; smoke returned `2026-10-31` |
| Factory Droid | native | `~/.factory/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions | installed; not smoke-tested |
| Kilo | native | `~/.config/kilo/AGENTS.md`, companions | `AGENTS.md`, companions | installed; not smoke-tested |
| Pi | native | `~/.pi/agent/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions | installed; not smoke-tested |
| Cline | native | `~/.agents/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions | installed; not smoke-tested |
| Central `.agents` | agents | `~/.agents/AGENTS.md`, companions, `skills/agents-contract` | `AGENTS.md`, companions | shared fallback; `--harness agents` |
| Gemini CLI | agents | `~/.gemini/GEMINI.md`, companions; central `.agents/skills` | `GEMINI.md`, companions | `0.66.0`; auth missing |
| Crush | agents | `~/.config/crush/CRUSH.md`, companions | `CRUSH.md`, companions | `v0.99.0`; API key rejected |
| Cursor | agents | UI-managed | `AGENTS.md`, companions | config present; binary not installed |
| Continue | alias | — (project only) | `AGENTS.md`, companions, `.continue/rules/agents-contract.md` | `cn` `1.5.47`; smoke request failed (interceptor error) |
| Aider | alias | `~/.aider.conf.yml` reads project `CONVENTIONS.md` | `CONVENTIONS.md`, `.aider.conf.yml`, companions | `0.86.2`; not smoke-tested |
| Qwen Code | alias | `~/.qwen/QWEN.md`, companions | `QWEN.md`, companions | `0.26.4`; auth missing |
| fx | agents | `~/.fx/AGENTS.md`, companions (regular files), `~/.fx/skills/agents-contract` | `AGENTS.md`, companions | `0.0.16`; smoke returned `2026-10-31` |
| Hermes | agents | `~/.hermes/skills/agents-contract`; project instructions only | `AGENTS.md`, companions | `v0.21.5`; not smoke-tested |
| OpenClaw / claw | agents | `~/.openclaw/workspace/AGENTS.md`, companions; `~/.agents/skills` fallback | `AGENTS.md`, companions | `2026.10.9`; headless smoke timed out before output |
| Jcode | agents | `~/AGENTS.md`, companions, `~/.jcode/skills/agents-contract` | `AGENTS.md`, companions | `v0.81.5`; smoke hit provider balance 402 |
| OMP | agents | `~/.omp/agent/AGENTS.md`, companions; `~/.agents/skills` fallback | `AGENTS.md`, companions | `v18.12.3`; smoke returned `2026-10-31` |
| Forge | agents | `~/forge/AGENTS.md`, companions, `~/forge/skills/agents-contract` | `AGENTS.md`, companions | `2.14.0`; not smoke-tested |
| Smelt | agents | `~/.config/smelt/AGENTS.md`, companions, `~/.config/smelt/skills/agents-contract` | `AGENTS.md`, companions | `v0.6.5`; not smoke-tested |
| Codewhale | agents | `~/.codewhale/skills/agents-contract`; project instructions only | `AGENTS.md`, companions | `0.10.2`; not smoke-tested |
| Copilot CLI | agents | `~/.copilot/copilot-instructions.md`; `~/.agents/skills` fallback | `AGENTS.md`, companions | `1.0.105`; not smoke-tested |

## Not installed

- **Windsurf** — GUI-managed; no CLI install or stable global file to test.

## Central fallback

`~/.agents/AGENTS.md` and `~/.agents/skills` are the shared fallback emitted by
the explicit `.agents` adapter and shared with Cline; `--harness auto` selects
them. OpenClaw, Copilot, Smelt, Codewhale, and fx also scan that skill directory.
`fx` additionally requires a real copy at `~/.fx/skills/agents-contract`, because
it refuses symlinked rule files and linked skill directories.

## Commands

```bash
python3 install.py --list-harnesses
python3 install.py --detect
python3 install.py --check --harness fx
python3 install.py --harness auto
python3 install.py --scope project --root /path/to/repo
```

The installer refuses foreign files, replaces them with `--force`, and reports
`unchanged` on an idempotent re-run. `--check` is read-only and exits 1 on stale
or missing selected paths. Restart the harness after a refresh: instruction and
skill metadata load at session start.
