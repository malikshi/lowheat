# Semble — instant local code search for agents

Semble is an MCP code-search server (with a CLI fallback) that locates code by
intent and returns ranked chunks with file and line. Upstream:
[`MinishLab/semble`](https://github.com/MinishLab/semble). It is the **top rung
of the discovery ladder** in `AGENTS.md` → Command Style → Tool ladder for code
discovery; this file holds the full reference. Verified against **semble 0.7.0**
— run `semble -V` for your build, and treat anything missing from `semble
--help` as unsupported.

## The one rule: discovery first, reading native

Semble answers *where* something lives, in a fraction of the tokens grep+read
costs. It does not answer *what a line says* — it returns ranked chunks, not
every occurrence, and its snippets are truncated to a line budget.

- Use semble to **find** the file and line. Then read that file with the native
  Read tool.
- Keep native Grep for exact `line:content` and for *every* occurrence of a
  literal string — semble returns top-k chunks, not an exhaustive match set.
- Semble is never a substitute for reading the code before you change it.

## The ladder

Locating code is not reading it. Take the first rung that answers the question:

1. **Semble MCP** — `search` / `find_related`, when the MCP server is
   connected. Fastest to call, no shell round-trip.
2. **Semble CLI** — `semble search "<query>" .` when the MCP is not wired in
   but the binary is on PATH.
3. **`rtk grep`** — a lossy survey: 0–90%+ smaller than native grep output
   (near-zero when a query has few matches). Answers "roughly where", not
   "give me every match".
4. **Native Grep/Glob** — the correctness floor: exact `line:content`, every
   occurrence, no caps. Always available, never lossy.

A missing rung drops to the next. Discovery is never blocked on an install; if
neither semble nor RTK is present, native Grep/Glob is always correct.

## When to use which

| You want | Use |
|---|---|
| "Where is X implemented?" | semble `search` |
| "What code resembles this location?" | semble `find_related` |
| Every occurrence of a literal string | native Grep |
| Exact `line:content` to feed an edit | native Read/Grep |
| Rough count / which files mention X, cheaply | `rtk grep` |
| Read a file (with or without a tool) | native Read — `rtk read` equals `cat` |

## CLI

```bash
semble search "how is auth validated" . --max-snippet-lines 10
semble find-related src/auth.py 42 .
semble search "deployment guide" . --content docs
semble search "database host port" . --content config
```

| Verb | Does |
|---|---|
| `search <query> [path...]` | Search a codebase (or several paths / git URLs together) |
| `find-related <file> <line> [path...]` | Code similar to a known location |
| `file-types` | Extensions indexed per content type |
| `savings` | Token savings and usage stats |
| `clear` | Clear the index cache |
| `install` / `uninstall` | Configure semble across coding agents |

Useful `search` flags: `-k/--top-k N` (results, default 5);
`--max-snippet-lines N` (10 = signature + body, 0 = no code);
`--format json|text` (default json); `--content code|docs|config|all`
(default code).

> The CLI verb is `find-related` (hyphen); the MCP tool is `find_related`
> (underscore). The CLI examples above were run and verified; the MCP tool
> names depend on how the harness registers the server.

## Install

```bash
uv tool install "semble[mcp]"                    # or: pipx install "semble[mcp]"
semble install --agent claude --type mcp -y      # wire the MCP server in
```

`semble install` configures agents non-interactively with `--agent`; `--type`
selects the integrations (`mcp`, `instructions`, `subagent`, or `all`). The
index builds on first run and is cached under `~/.cache/semble`; `semble clear`
drops it.

If semble is not installed, everything still works: drop to `rtk grep` or
native Grep/Glob. Never block on the install.

## Caveats

- **~4s per CLI call, no warm-cache speedup.** Each invocation reloads the
  model; the index cache avoids re-indexing, not re-loading. The MCP server
  pays that cost once per session, which is why it is rung 1.
- **Top-k, not exhaustive.** `search` returns ranked chunks — it is not a
  match-complete search. Confirm with native Grep when "every hit" matters.
- **Snippets are truncated** to the snippet-line budget; the surrounding file
  is not in the result. Read the file for context.
- **Raises when a content type matches no files** — `--content config` in a repo
  with no config files exits with `ValueError: No supported files found under
  <path>`, not empty results. Expected, not a bug; pick a content type the repo
  actually has.
