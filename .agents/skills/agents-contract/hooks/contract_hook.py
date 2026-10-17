"""contract_hook.py — Entry point the three harnesses run as a hook.

exports: main
used_by: .agents/skills/agents-contract/hooks/install_hooks.py → wires this file as the hook command [cascade]
used_by: tests/test_contract_hook.py → main [cascade]
related: hook_policy.py holds the decisions; hook_harness.py holds detection and the reply shapes.
rules:   Fail open. A malformed payload, a non-object payload, or an unexpected internal error must exit 0 and leave the tool call alone — a hook that cannot decide never blocks work. The reply is the only stdout line, because every harness parses stdout as JSON.
agent:   grok-build | xai | 2026-10-17 | 01a14a7c-788f-7061-83bb-6dded52bc3b5 | first cut: stdin payload → decide → encode, silent on unparseable input, one stderr breadcrumb on an internal error
agent:   grok-build | xai | 2026-10-18 | 01a14ad3-ab3e-74b1-81d5-fc6f08b61af7 | on review: the reply write is guarded too, so a harness that closes the pipe returns 0 instead of raising BrokenPipeError
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import hook_harness
import hook_policy


def main(argv=None, stdin=None, stdout=None) -> int:
    """Read one hook event, print the reply the harness expects, and exit 0.

    Rules:   Never raise and never exit non-zero. Unparseable or non-object input prints nothing at all; an internal failure prints nothing on stdout and one line on stderr so the harness records it without feeding the model a broken reply.
    """
    stream = stdin if stdin is not None else sys.stdin
    sink = stdout if stdout is not None else sys.stdout
    try:
        payload = json.loads(stream.read() or "")
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        decision = hook_policy.decide(payload)
        reply = hook_harness.encode(
            hook_harness.detect_harness(payload, os.environ), decision
        )
    except Exception as error:
        print(f"contract_hook: {type(error).__name__}: {error}", file=sys.stderr)
        return 0
    if reply:
        try:
            print(json.dumps(reply), file=sink)
        except OSError:
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
