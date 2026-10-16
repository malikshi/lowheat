"""bench/discovery_tokens.py — Measure tokens per code-discovery query across the ladder.

exports: main | measure_native_grep | measure_rtk_grep | measure_semble | QUERIES
used_by: none
rules:   Read-only — never writes to the corpus. A tool that is absent or errors is reported as unavailable, never silently scored as zero. Tokens use tiktoken when importable, else bytes/4 as a labelled estimate. Reads are excluded from the comparison on purpose: `rtk read` is byte-identical to `cat`, so it has no token advantage to measure.
agent:   unknown | unknown | 2026-10-16 | s_bench | initial harness; tokens measured with tiktoken on a Python corpus showed rtk's win is `rtk grep`, not `rtk read`, and semble ~99% below grep+read.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

try:
    import tiktoken

    _ENC = tiktoken.get_encoding("cl100k_base")

    def count_tokens(text: str) -> int:
        """Count tokens with the real tokenizer.

        Rules:   cl100k_base is a fixed reference so runs are comparable across machines.
        """
        return len(_ENC.encode(text))

    TOKENIZER = "tiktoken/cl100k_base"
except Exception:  # tiktoken absent — fall back to the bytes/4 estimate

    def count_tokens(text: str) -> int:
        """Estimate tokens as bytes/4 when no tokenizer is installed.

        Rules:   Labelled as an estimate in the report; absolute numbers are approximate, ratios stay usable.
        """
        return len(text.encode("utf-8")) // 4

    TOKENIZER = "bytes/4 (estimate — install tiktoken for exact counts)"

MAX_READ_FILES = 5
DEFAULT_SCOPE = ("src", "lib", "app", "python", "scripts", "shell", "manager", "internal", "pkg", "cmd")

QUERIES = (
    ("firewall install", "setup_mariadb"),
    ("wireguard config", "wireguard"),
    ("renew user", "renew"),
    ("traffic stats", "traffic"),
    ("vpn client api", "zivpn"),
    ("database backup", "mariadb"),
    ("nginx config", "nginx"),
    ("cloudflare dns", "cloudflare"),
)


def _run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[str, int]:
    """Run argv directly and return combined output plus exit code.

    Rules:   No shell; a missing binary or timeout returns empty output with a non-zero code, never raising.
    """
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout + proc.stderr, proc.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "", 127


def _scope_dirs(corpus: Path) -> list[str]:
    """Return the existing top-level directories to search.

    Rules:   A scope name that does not exist is dropped; passing it would make grep and semble error and read as zero tokens.
    """
    return [name for name in DEFAULT_SCOPE if (corpus / name).is_dir()]


def _matched_files(grep_out: str, corpus: Path, limit: int) -> list[str]:
    """Pick the most-matched files from grep output, most matches first.

    Rules:   Both readers get this same list so a token delta reflects the reader, not the file pick.
    """
    counts: dict[str, int] = {}
    for line in grep_out.splitlines():
        file_part = line.split(":", 1)[0].removeprefix("./")
        if (corpus / file_part).is_file():
            counts[file_part] = counts.get(file_part, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [name for name, _ in ranked[:limit]]


def measure_native_grep(corpus: Path, keyword: str, scope: list[str]) -> dict:
    """Measure native grep output plus the files an agent would then read.

    Rules:   Reproduces the grep+read baseline semble benchmarks against; read cost uses `cat` (the lossless read).
    """
    started = time.time()
    out, _ = _run(["grep", "-rn", "--", keyword, *scope], corpus)
    grep_tokens = count_tokens(out)
    read_tokens = 0
    for name in _matched_files(out, corpus, MAX_READ_FILES):
        file_text, _ = _run(["cat", name], corpus)
        read_tokens += count_tokens(file_text)
    return {
        "tool": "native grep+read",
        "available": True,
        "tokens": grep_tokens + read_tokens,
        "detail": f"grep {grep_tokens} + read {read_tokens}",
        "secs": round(time.time() - started, 2),
    }


def measure_rtk_grep(corpus: Path, keyword: str, scope: list[str]) -> dict:
    """Measure `rtk grep` output plus the files an agent would then read.

    Rules:   rtk's own flags must precede the pattern (`--max=N`); placed after it they leak to GNU grep and error. Read cost uses `rtk read`, byte-identical to `cat`, so it mirrors the native rung.
    """
    if not shutil.which("rtk"):
        return {"tool": "rtk grep+read", "available": False, "tokens": 0, "detail": "rtk not on PATH"}
    started = time.time()
    out, code = _run(["rtk", "grep", "-rn", "--max=100000", "--", keyword, *scope], corpus)
    if code != 0 and not out:
        return {"tool": "rtk grep+read", "available": False, "tokens": 0, "detail": f"exit {code}"}
    grep_tokens = count_tokens(out)
    read_tokens = 0
    for name in _matched_files(out, corpus, MAX_READ_FILES):
        file_text, _ = _run(["rtk", "read", name], corpus)
        read_tokens += count_tokens(file_text)
    return {
        "tool": "rtk grep+read",
        "available": True,
        "tokens": grep_tokens + read_tokens,
        "detail": f"grep {grep_tokens} + read {read_tokens}",
        "secs": round(time.time() - started, 2),
    }


def measure_semble(corpus: Path, query: str) -> dict:
    """Measure one `semble search` call's ranked-chunk payload.

    Rules:   JSON output is the agent-visible payload; a parse failure is reported as unavailable rather than counted as a hit.
    """
    if not shutil.which("semble"):
        return {"tool": "semble search", "available": False, "tokens": 0, "detail": "semble not on PATH"}
    started = time.time()
    out, code = _run(["semble", "search", query, ".", "--max-snippet-lines", "10"], corpus)
    if code != 0 or not out:
        return {"tool": "semble search", "available": False, "tokens": 0, "detail": f"exit {code}"}
    try:
        results = json.loads(out).get("results", [])
    except json.JSONDecodeError:
        return {"tool": "semble search", "available": False, "tokens": 0, "detail": "unparseable JSON"}
    top = results[0]["file_path"] if results else None
    return {
        "tool": "semble search",
        "available": True,
        "tokens": count_tokens(out),
        "detail": f"{len(results)} results, top={top}",
        "secs": round(time.time() - started, 2),
    }


def main() -> int:
    """Run the ladder benchmark over the query set and print a token table.

    Rules:   Corpus must be a directory; exit 2 when it is not, so a typo never reads as a clean run.
    """
    parser = argparse.ArgumentParser(description="Compare code-discovery token cost: semble vs rtk vs native.")
    parser.add_argument("corpus", type=Path, help="directory to search")
    parser.add_argument("--limit", type=int, default=len(QUERIES), help="number of queries to run")
    args = parser.parse_args()
    if not args.corpus.is_dir():
        print(f"error: not a directory: {args.corpus}", file=sys.stderr)
        return 2
    scope = _scope_dirs(args.corpus)
    if not scope:
        print("error: no known source directories found in corpus", file=sys.stderr)
        return 2

    print(f"corpus: {args.corpus}")
    print(f"scope : {', '.join(scope)}")
    print(f"tokens: {TOKENIZER}\n")
    header = f"{'query':<18}{'native':>10}{'rtk':>10}{'semble':>10}  semble top"
    print(header)
    print("-" * len(header))
    totals = {"native": 0, "rtk": 0, "semble": 0}
    for query, keyword in QUERIES[: args.limit]:
        native = measure_native_grep(args.corpus, keyword, scope)
        rtk = measure_rtk_grep(args.corpus, keyword, scope)
        semble = measure_semble(args.corpus, query)
        totals["native"] += native["tokens"]
        totals["rtk"] += rtk["tokens"]
        totals["semble"] += semble["tokens"]
        top = semble["detail"].split("top=", 1)[-1] if "top=" in semble["detail"] else "-"
        print(f"{query:<18}{native['tokens']:>10}{rtk['tokens']:>10}{semble['tokens']:>10}  {top}")

    print("\nTOTAL", totals)
    base = totals["native"] or 1
    if totals["rtk"]:
        print(f"rtk    vs native: {(base - totals['rtk']) / base * 100:+.1f}%")
    print(f"semble vs native: {(base - totals['semble']) / base * 100:+.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
