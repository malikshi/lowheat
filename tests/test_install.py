"""test_install.py — Tests for the per-harness contract installer.

exports: class InstallerTestCase | class GrokRulesTestCase | class MirrorTestCase
used_by: none
rules:   Load install.py by file path — the repo root is not a package. Every case runs against a temporary home so a test never rewrites real harness configs, and every emitted link must resolve to the contract source.
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-23 | 81e2ea63-c0ca-489d-a506-5ec094106a17 | first cut: asserted the per-harness shapes after Grok was found not to expand @-imports, so it needs the companions as standalone rules files while the other two get one symlink
"""

from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

install = importlib.import_module("install")


class InstallerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.home, ignore_errors=True))

    def test_claude_gets_a_link_for_each_memory_filename_it_reads(self) -> None:
        plans = install.plan_harnesses(self.home)
        links = plans["claude"].links

        self.assertIn(self.home / ".claude" / "AGENTS.md", links)
        self.assertIn(self.home / ".claude" / "CLAUDE.md", links)

    def test_commandcode_gets_agents_md_only(self) -> None:
        plans = install.plan_harnesses(self.home)
        links = plans["commandcode"].links

        self.assertEqual([self.home / ".commandcode" / "AGENTS.md"], list(links))

    def test_apply_creates_links_that_resolve_to_the_contract(self) -> None:
        plan = install.plan_harnesses(self.home)["claude"]

        install.apply_plan(plan, install.CONTRACT_DIR, dry_run=False)

        for target in plan.links:
            self.assertTrue(target.exists(), target)

    def test_second_run_reports_unchanged_instead_of_relinking(self) -> None:
        plan = install.plan_harnesses(self.home)["claude"]
        install.apply_plan(plan, install.CONTRACT_DIR, dry_run=False)

        actions = install.apply_plan(plan, install.CONTRACT_DIR, dry_run=False)

        self.assertTrue(all("unchanged" in action for action in actions), actions)

    def test_dry_run_reports_unchanged_and_writes_nothing(self) -> None:
        plan = install.plan_harnesses(self.home)["claude"]
        install.apply_plan(plan, install.CONTRACT_DIR, dry_run=False)

        actions = install.apply_plan(plan, install.CONTRACT_DIR, dry_run=True)

        self.assertTrue(all("unchanged" in action for action in actions), actions)


class GrokRulesTestCase(unittest.TestCase):
    def test_grok_gets_every_companion_as_a_standalone_rule(self) -> None:
        plan = install.plan_harnesses(Path("/tmp/any"))["grok"]

        self.assertIsNotNone(plan.rules_dir)
        rendered = install.render_grok_rules(install.CONTRACT_DIR)
        self.assertEqual(set(install.COMPANIONS), set(rendered))

    def test_rendered_rules_match_the_contract_files(self) -> None:
        rendered = install.render_grok_rules(install.CONTRACT_DIR)

        for name, text in rendered.items():
            self.assertEqual(
                (install.CONTRACT_DIR / name).read_text(encoding="utf-8"), text
            )


class MirrorTestCase(unittest.TestCase):
    def test_mirror_is_byte_identical_to_the_contract(self) -> None:
        target = install.sync_contract_mirror(install.CONTRACT_DIR, install.SKILL_DIR)

        self.assertEqual(
            (install.CONTRACT_DIR / "AGENTS.md").read_bytes(), target.read_bytes()
        )


class ProjectScopeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(
            lambda: __import__("shutil").rmtree(self.root, ignore_errors=True)
        )

    def apply(self, dry_run: bool = False) -> list[str]:
        actions: list[str] = []
        emitted: set = set()
        for plan in install.plan_project(self.root).values():
            unique = install.HarnessPlan(
                plan.harness,
                {t: s for t, s in plan.links.items() if t not in emitted},
                plan.rules_dir,
                plan.copy,
            )
            emitted.update(unique.links)
            actions.extend(install.apply_plan(unique, install.CONTRACT_DIR, dry_run))
        return actions

    def test_project_install_writes_real_files_not_symlinks(self) -> None:
        self.apply()

        for name in ("AGENTS.md", "CLAUDE.md", "RTK.md", "semble.md"):
            path = self.root / name
            self.assertTrue(path.is_file(), path)
            self.assertFalse(path.is_symlink(), path)

    def test_project_install_carries_no_absolute_path_to_the_source_checkout(self) -> None:
        self.apply()

        for path in self.root.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn(str(install.CONTRACT_DIR), text, path)

    def test_project_files_keep_the_imports_that_reach_the_companions(self) -> None:
        self.apply()

        contract = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("@RTK.md", contract)

    def test_second_project_run_reports_unchanged(self) -> None:
        self.apply()

        actions = self.apply()

        self.assertTrue(all("unchanged" in action for action in actions), actions)


class ConflictGuardTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(
            lambda: __import__("shutil").rmtree(self.root, ignore_errors=True)
        )
        self.plans = install.plan_project(self.root)
        self.chosen = install.HARNESSES

    def test_foreign_agents_md_is_reported_once_as_a_conflict(self) -> None:
        (self.root / "AGENTS.md").write_text("MY OWN RULES\n", encoding="utf-8")

        conflicts = install.find_conflicts(self.plans, self.chosen)

        self.assertEqual([self.root / "AGENTS.md"], conflicts)

    def test_install_refuses_a_foreign_agents_md_and_leaves_it_intact(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("MY OWN RULES\n", encoding="utf-8")

        code = install.main(
            ["--scope", "project", "--root", str(self.root), "--no-hooks"]
        )

        self.assertEqual(1, code)
        self.assertEqual("MY OWN RULES\n", agents.read_text(encoding="utf-8"))

    def test_force_replaces_a_foreign_agents_md_and_keeps_a_backup(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("MY OWN RULES\n", encoding="utf-8")

        code = install.main(
            ["--scope", "project", "--root", str(self.root), "--no-hooks", "--force"]
        )

        self.assertEqual(0, code)
        self.assertNotEqual("MY OWN RULES\n", agents.read_text(encoding="utf-8"))
        self.assertEqual(
            "MY OWN RULES\n",
            (self.root / "AGENTS.md.bak").read_text(encoding="utf-8"),
        )

    def test_a_matching_file_is_not_a_conflict_so_re_runs_stay_quiet(self) -> None:
        self.apply()

        self.assertEqual([], install.find_conflicts(self.plans, self.chosen))

    def test_a_symlink_is_never_a_conflict(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.symlink_to(install.CONTRACT_DIR / "RTK.md")

        self.assertEqual([], install.find_conflicts(self.plans, self.chosen))

    def apply(self) -> None:
        install.main(["--scope", "project", "--root", str(self.root), "--no-hooks"])


if __name__ == "__main__":
    unittest.main()
