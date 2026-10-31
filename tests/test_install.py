"""test_install.py — Tests for the per-harness contract installer.

exports: class ConflictGuardTestCase | class DryRunTestCase | class GrokRulesTestCase | class InstallerTestCase | class MirrorTestCase | class ProjectScopeTestCase
used_by: none
rules:   Load install.py by file path — the repo root is not a package. Every case runs against a temporary home or root so a test never rewrites real harness configs, and every emitted link must resolve to the contract source or the skill source. The contract is thin and names companions by filename, so the cases assert those files ship beside it and no `@` import is required.
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-23 | 81e2ea63-c0ca-489d-a506-5ec094106a17 | first cut: asserted the per-harness shapes after Grok was found not to expand @-imports, so it needs the companions as standalone rules files while the other two get one symlink
agent:   deepseek-v4.1-flash | nexrouter | 2026-10-24 | 372685f1-d81d-4c7c-8fbb-7e8e636e8b48 | added the per-harness companion-import check: the existing project case applies every plan at once, so Claude's companions satisfied the imports for all three and the commandcode-only case went untested. Each subtest now gets its own root.
agent:   fx | unknown | 2026-10-31 | unknown | dropped hook wiring, vendored-skill cases, and the cleanup pass after the one-shot removal tool was deleted
agent:   fx | unknown | 2026-10-31 | unknown | covered the user-scope companion links, skill links, and both reference mirrors; added a real skill directory as a refusal case
agent:   fx | unknown | 2026-10-31 | unknown | thin-contract restructure: project cases now assert every named companion ships and AGENTS.md carries no @ imports
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

    def test_user_scope_links_every_companion_beside_the_contract(self) -> None:
        plans = install.plan_harnesses(self.home)

        for harness in ("claude", "commandcode"):
            with self.subTest(harness=harness):
                base = self.home / install.HOME_DIR[harness]
                for name in install.COMPANIONS:
                    self.assertEqual(
                        install.CONTRACT_DIR / name, plans[harness].links[base / name]
                    )

    def test_user_scope_links_the_skill_into_each_harness(self) -> None:
        plans = install.plan_harnesses(self.home)

        for harness in install.HARNESSES:
            with self.subTest(harness=harness):
                base = self.home / install.HOME_DIR[harness]
                self.assertEqual(
                    install.SKILL_DIR,
                    plans[harness].links[base / "skills" / install.SKILL_DIR.name],
                )

    def test_commandcode_gets_agents_md_without_claude_filename(self) -> None:
        plans = install.plan_harnesses(self.home)
        links = plans["commandcode"].links

        self.assertIn(self.home / ".commandcode" / "AGENTS.md", links)
        self.assertNotIn(self.home / ".commandcode" / "CLAUDE.md", links)

    def test_every_user_harness_ships_the_companions_it_names(self) -> None:
        plans = install.plan_harnesses(self.home)

        for harness in ("claude", "commandcode"):
            with self.subTest(harness=harness):
                plan = plans[harness]
                install.apply_plan(plan, install.CONTRACT_DIR, dry_run=False)
                base = self.home / install.HOME_DIR[harness]
                missing = [
                    name for name in install.COMPANIONS if not (base / name).is_file()
                ]
                self.assertEqual([], missing, harness)

    def test_a_real_skill_directory_is_refused_not_replaced(self) -> None:
        skill = self.home / ".claude" / "skills" / install.SKILL_DIR.name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("MY OWN SKILL\n", encoding="utf-8")

        conflicts = install.find_conflicts(
            install.plan_harnesses(self.home), ("claude",), install.CONTRACT_DIR
        )

        self.assertEqual([skill], conflicts)

    def test_a_directory_at_a_file_target_is_refused(self) -> None:
        agents = self.home / ".claude" / "AGENTS.md"
        agents.mkdir(parents=True)

        conflicts = install.find_conflicts(
            install.plan_harnesses(self.home), ("claude",), install.CONTRACT_DIR
        )

        self.assertEqual([agents], conflicts)

    def test_force_backs_up_a_real_skill_directory_before_replacing_it(self) -> None:
        skill = self.home / ".claude" / "skills" / install.SKILL_DIR.name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("MY OWN SKILL\n", encoding="utf-8")

        code = install.main(["--home", str(self.home), "--harness", "claude", "--force"])

        self.assertEqual(0, code)
        self.assertTrue(skill.is_symlink())
        backup = skill.with_name(skill.name + ".bak")
        self.assertEqual(
            "MY OWN SKILL\n", (backup / "SKILL.md").read_text(encoding="utf-8")
        )

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
    def test_all_mirrors_are_byte_identical_to_their_sources(self) -> None:
        targets = install.sync_contract_mirror(install.CONTRACT_DIR, install.SKILL_DIR)

        self.assertEqual(
            [
                install.SKILL_DIR / "references" / "contract.md",
                install.SKILL_DIR / "references" / "codedna.md",
                install.SKILL_DIR / "references" / "commands.md",
            ],
            targets,
        )
        for source, target in zip(
            ("AGENTS.md", "codedna.md", "RTK.md"), targets, strict=True
        ):
            self.assertEqual((install.CONTRACT_DIR / source).read_bytes(), target.read_bytes())


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

        for name in ("AGENTS.md", "CLAUDE.md", *install.COMPANIONS):
            path = self.root / name
            self.assertTrue(path.is_file(), path)
            self.assertFalse(path.is_symlink(), path)

    def test_project_install_carries_no_absolute_path_to_the_source_checkout(self) -> None:
        self.apply()

        for path in self.root.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".json"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotIn(str(install.CONTRACT_DIR), text, path)

    def test_project_contract_names_every_companion_and_imports_none(self) -> None:
        self.apply()

        contract = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertNotRegex(contract, r"(?m)^@\S+$")
        for name in install.COMPANIONS:
            self.assertIn(name, contract)

    def test_every_project_harness_ships_the_companions_it_names(self) -> None:
        for harness in install.HARNESSES:
            with self.subTest(harness=harness):
                root = Path(tempfile.mkdtemp())
                self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
                install.main(
                    [
                        "--scope",
                        "project",
                        "--root",
                        str(root),
                        "--harness",
                        harness,
                    ]
                )
                missing = [
                    name for name in install.COMPANIONS if not (root / name).is_file()
                ]
                self.assertEqual([], missing, harness)

    def test_second_project_run_reports_unchanged(self) -> None:
        self.apply()

        actions = self.apply()

        self.assertTrue(all("unchanged" in action for action in actions), actions)


class DryRunTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.home, ignore_errors=True))

    def test_dry_run_writes_no_harness_settings(self) -> None:
        install.main(
            ["--home", str(self.home), "--harness", "commandcode", "--dry-run"]
        )

        self.assertFalse((self.home / ".commandcode" / "settings.json").exists())


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

        conflicts = install.find_conflicts(self.plans, self.chosen, install.CONTRACT_DIR)

        self.assertEqual([self.root / "AGENTS.md"], conflicts)

    def test_install_refuses_a_foreign_agents_md_and_leaves_it_intact(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("MY OWN RULES\n", encoding="utf-8")

        code = install.main(["--scope", "project", "--root", str(self.root)])

        self.assertEqual(1, code)
        self.assertEqual("MY OWN RULES\n", agents.read_text(encoding="utf-8"))

    def test_force_replaces_a_foreign_agents_md_and_keeps_a_backup(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("MY OWN RULES\n", encoding="utf-8")

        code = install.main(
            ["--scope", "project", "--root", str(self.root), "--force"]
        )

        self.assertEqual(0, code)
        self.assertNotEqual("MY OWN RULES\n", agents.read_text(encoding="utf-8"))
        self.assertEqual(
            "MY OWN RULES\n",
            (self.root / "AGENTS.md.bak").read_text(encoding="utf-8"),
        )

    def test_a_matching_file_is_not_a_conflict_so_re_runs_stay_quiet(self) -> None:
        self.apply()

        self.assertEqual(
            [], install.find_conflicts(self.plans, self.chosen, install.CONTRACT_DIR)
        )

    def test_a_symlink_is_never_a_conflict(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.symlink_to(install.CONTRACT_DIR / "RTK.md")

        self.assertEqual(
            [], install.find_conflicts(self.plans, self.chosen, install.CONTRACT_DIR)
        )

    def test_a_foreign_grok_rules_file_is_a_conflict(self) -> None:
        rules = self.root / ".grok" / "rules"
        rules.mkdir(parents=True)
        (rules / "RTK.md").write_text("MY OWN\n", encoding="utf-8")

        conflicts = install.find_conflicts(self.plans, self.chosen, install.CONTRACT_DIR)

        self.assertEqual([rules / "RTK.md"], conflicts)

    def test_install_refuses_a_foreign_grok_rules_file(self) -> None:
        rules = self.root / ".grok" / "rules"
        rules.mkdir(parents=True)
        own = rules / "RTK.md"
        own.write_text("MY OWN\n", encoding="utf-8")

        code = install.main(["--scope", "project", "--root", str(self.root)])

        self.assertEqual(1, code)
        self.assertEqual("MY OWN\n", own.read_text(encoding="utf-8"))

    def test_project_scope_refuses_the_source_checkout_itself(self) -> None:
        before = sorted(p.name for p in install._HERE.iterdir())

        code = install.main(["--scope", "project", "--root", str(install._HERE)])

        self.assertEqual(1, code)
        self.assertEqual(before, sorted(p.name for p in install._HERE.iterdir()))

    def apply(self) -> None:
        install.main(["--scope", "project", "--root", str(self.root)])


if __name__ == "__main__":
    unittest.main()
