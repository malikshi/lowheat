"""test_discovery_tokens.py — Tests for the discovery-token benchmark helpers.

exports: class DiscoveryBenchTestCase
used_by: none
rules:   Import the bench module by file path — `bench/` is not a Python package. Never shell out to real rtk/semble/grep; stub subprocess so the test is hermetic and fast.
agent:   unknown | unknown | 2026-10-16 | s_bench | added helper tests after the initial harness.
agent:   fx | unknown | 2026-11-05 | unknown | covered query parsing, scope fallback, tool errors, and n/a comparisons
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO = Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("discovery_tokens", _REPO / "bench" / "discovery_tokens.py")
assert spec and spec.loader
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)


class DiscoveryBenchTestCase(unittest.TestCase):
    def test_scope_dirs_prefers_known_source_names(self) -> None:
        corpus = Path(self._corpus())
        (corpus / "src").mkdir()

        self.assertEqual(["src"], bench._scope_dirs(corpus))

    def test_scope_dirs_falls_back_to_nonhidden_top_level_entries(self) -> None:
        corpus = Path(self._corpus())
        (corpus / "docs").mkdir()
        (corpus / "__pycache__").mkdir()
        (corpus / "node_modules").mkdir()

        self.assertEqual(["a.py", "b.py", "docs"], bench._scope_dirs(corpus))

    def test_scope_dirs_returns_root_files_for_a_flat_corpus(self) -> None:
        corpus = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(corpus, ignore_errors=True))
        (corpus / "main.py").write_text("def helper():\n    return 1\n", encoding="utf-8")

        self.assertEqual(["main.py"], bench._scope_dirs(corpus))

    def test_query_pairs_defaults_and_explicit_keywords(self) -> None:
        self.assertEqual(bench.QUERIES, bench._query_pairs(None))
        self.assertEqual(
            (("firewall install", "firewall"), ("vpn api", "zivpn")),
            bench._query_pairs(["firewall install", "vpn api=zivpn"]),
        )

    def test_native_grep_reports_an_error_as_unavailable(self) -> None:
        with mock.patch.object(bench, "_run", return_value=("grep: boom\n", 2)):
            result = bench.measure_native_grep(Path("/tmp"), "kw", ["."])

        self.assertFalse(result["available"])
        self.assertEqual(0, result["tokens"])

    def test_rtk_grep_reports_an_error_as_unavailable(self) -> None:
        with mock.patch.object(bench.shutil, "which", return_value="/bin/rtk"), mock.patch.object(
            bench, "_run", return_value=("rtk: boom\n", 2)
        ):
            result = bench.measure_rtk_grep(Path("/tmp"), "kw", ["."])

        self.assertFalse(result["available"])

    def test_comparison_is_n_a_when_native_total_is_zero(self) -> None:
        lines = bench._comparison_lines(
            {"native": 0, "rtk": 0, "semble": 10},
            {"native": 1, "rtk": 1, "semble": 1},
            1,
        )

        self.assertTrue(all("n/a" in line for line in lines), lines)

    def test_comparison_is_n_a_when_a_tool_was_unavailable(self) -> None:
        lines = bench._comparison_lines(
            {"native": 100, "rtk": 0, "semble": 50},
            {"native": 2, "rtk": 1, "semble": 2},
            2,
        )

        self.assertEqual(2, len(lines))
        self.assertIn("rtk", lines[0])
        self.assertIn("n/a", lines[0])
        self.assertIn("+50.0%", lines[1])

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
