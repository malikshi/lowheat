"""test_discovery_tokens.py — Tests for the discovery-token benchmark helpers.

exports: class DiscoveryBenchTestCase
used_by: none
rules:   Import the bench module by file path — `bench/` is not a Python package. Never shell out to real rtk/semble/grep; stub subprocess so the test is hermetic and fast.
agent:   unknown | unknown | 2026-10-16 | s_bench | added helper tests after the initial harness.
"""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("discovery_tokens", _REPO / "bench" / "discovery_tokens.py")
assert spec and spec.loader
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class DiscoveryBenchTestCase(unittest.TestCase):
    def test_scope_dirs_drops_missing_names(self) -> None:
        # Rules: a scope name that does not exist would error grep/semble and read as zero tokens.
        self.assertEqual(bench._scope_dirs(_REPO), [])

    def test_matched_files_ranks_by_hit_count(self) -> None:
        corpus = Path(self._corpus())
        grep_out = "./b.py:1:x\n./a.py:2:x\n./a.py:3:x\n./a.py:4:x\n./b.py:5:x\n"
        self.assertEqual(bench._matched_files(grep_out, corpus, 5), ["a.py", "b.py"])

    def test_matched_files_ignores_paths_outside_corpus(self) -> None:
        corpus = Path(self._corpus())
        grep_out = "./ghost.py:1:x\n"
        self.assertEqual(bench._matched_files(grep_out, corpus, 5), [])

    def test_measure_semble_reports_absent_tool(self) -> None:
        with mock.patch.object(bench.shutil, "which", return_value=None):
            result = bench.measure_semble(Path("/tmp"), "anything")
        self.assertFalse(result["available"])
        self.assertEqual(result["tokens"], 0)

    def test_measure_rtk_reports_absent_tool(self) -> None:
        with mock.patch.object(bench.shutil, "which", return_value=None):
            result = bench.measure_rtk_grep(Path("/tmp"), "kw", ["."])
        self.assertFalse(result["available"])

    def test_count_tokens_is_positive(self) -> None:
        self.assertGreater(bench.count_tokens("def helper() -> int:\n    return 1\n"), 0)

    @staticmethod
    def _corpus() -> str:
        import tempfile

        d = tempfile.mkdtemp()
        (Path(d) / "a.py").write_text("x\n")
        (Path(d) / "b.py").write_text("x\n")
        return d


if __name__ == "__main__":
    unittest.main()
