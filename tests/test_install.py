"""test_install.py — Tests for the per-harness contract installer.

exports: class ConflictGuardTestCase | class DryRunTestCase | class GrokRulesTestCase | class InstallerTestCase | class MirrorTestCase | class ProjectScopeTestCase
used_by: none
rules:   Load install.py by file path — the repo root is not a package. Every case runs against a temporary home or root so a test never rewrites real harness configs, and every emitted link must resolve to the contract source or the skill source. The contract is thin and names companions by filename, so the cases assert those files ship beside it and no `@` import is required. Directory comparisons ignore Python bytecode caches.
agent:   fx | unknown | 2026-10-31 | unknown | dropped hook wiring, vendored-skill cases, and the cleanup pass after the one-shot removal tool was deleted
agent:   fx | unknown | 2026-10-31 | unknown | covered the user-scope companion links, skill links, and both reference mirrors; added a real skill directory as a refusal case
agent:   fx | unknown | 2026-10-31 | unknown | thin-contract restructure: project cases now assert every named companion ships and AGENTS.md carries no @ imports
agent:   fx | unknown | 2026-10-31 | unknown | added the bytecode-cache regression for the installer's copied-skill comparison
agent:   fx | unknown | 2026-11-05 | unknown | covered force-directory replacement, path validation, project-only no-op, list/detect, and mirror dry-run
"""

from __future__ import annotations

import importlib
import io
import contextlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

install = importlib.import_module("install")


class InstallerTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(self.home, ignore_errors=True))

    def test_same_tree_ignores_python_bytecode(self) -> None:
        left = self.home / "left"
        right = self.home / "right"
        for root in (left, right):
            root.mkdir()
            (root / "sample.py").write_text("value = 1\n", encoding="utf-8")
        (left / "__pycache__").mkdir()
        (left / "__pycache__" / "sample.cpython-311.pyc").write_bytes(b"cache")
        self.assertTrue(install._same_tree(left, right))

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

    def test_user_scope_links_the_skill_into_each_capable_harness(self) -> None:
        plans = install.plan_harnesses(self.home)

        for spec in install.SPECS:
            if not spec.global_install or not spec.skill_dir:
                continue
            with self.subTest(harness=spec.name):
                base = self.home / spec.config_dir
                target = base / spec.skill_dir / install.SKILL_DIR.name
                if spec.copy_skill:
                    self.assertEqual(install.SKILL_DIR, plans[spec.name].dirs[target])
                else:
                    self.assertEqual(install.SKILL_DIR, plans[spec.name].links[target])

    def test_codex_opencode_factory_kilo_pi_and_cline_get_contracts(self) -> None:
        plans = install.plan_harnesses(self.home)

        for harness in ("codex", "opencode", "factory", "kilo", "pi", "cline"):
            with self.subTest(harness=harness):
                base = self.home / install.HOME_DIR[harness]
                self.assertEqual(
                    install.CONTRACT_DIR / "AGENTS.md", plans[harness].links[base / "AGENTS.md"]
                )

    def test_gemini_uses_gemini_md(self) -> None:
        plan = install.plan_harnesses(self.home)["gemini"]
        base = self.home / ".gemini"

        self.assertEqual(install.CONTRACT_DIR / "AGENTS.md", plan.links[base / "GEMINI.md"])
        self.assertNotIn(base / "AGENTS.md", plan.links)

    def test_gemini_crush_and_qwen_use_their_aliases(self) -> None:
        plans = install.plan_harnesses(self.home)

        for harness, alias in (
            ("gemini", "GEMINI.md"),
            ("crush", "CRUSH.md"),
            ("qwen", "QWEN.md"),
        ):
            with self.subTest(harness=harness):
                base = self.home / install.HOME_DIR[harness]
                self.assertEqual(
                    install.CONTRACT_DIR / "AGENTS.md", plans[harness].links[base / alias]
                )
                self.assertNotIn(base / "AGENTS.md", plans[harness].links)

    def test_aider_gets_global_config_and_project_alias(self) -> None:
        user = install.plan_harnesses(self.home)["aider"]
        project = install.plan_project(self.home)["aider"]

        self.assertEqual(
            install.CONTRACT_DIR / "aider.conf.yml",
            user.links[self.home / ".aider.conf.yml"],
        )
        self.assertEqual(
            install.CONTRACT_DIR / "AGENTS.md",
            project.links[self.home / "CONVENTIONS.md"],
        )
        self.assertEqual(
            install.CONTRACT_DIR / "aider.conf.yml",
            project.links[self.home / ".aider.conf.yml"],
        )

    def test_continue_writes_a_project_rule(self) -> None:
        project = install.plan_project(self.home)["continue"]

        self.assertEqual(
            install.CONTRACT_DIR / "continue.md",
            project.links[self.home / ".continue/rules/agents-contract.md"],
        )
        self.assertNotIn("continue", install.plan_harnesses(self.home))

    def test_named_harnesses_map_to_their_global_surfaces(self) -> None:
        plans = install.plan_harnesses(self.home)
        cases = {
            "fx": self.home / ".fx" / "AGENTS.md",
            "hermes": self.home / ".hermes" / "skills" / "agents-contract",
            "claw": self.home / ".openclaw" / "workspace" / "AGENTS.md",
            "jcode": self.home / "AGENTS.md",
            "omp": self.home / ".omp" / "agent" / "AGENTS.md",
            "forge": self.home / "forge" / "AGENTS.md",
            "smelt": self.home / ".config" / "smelt" / "AGENTS.md",
            "codewhale": self.home / ".codewhale" / "skills" / "agents-contract",
            "copilot": self.home / ".copilot" / "copilot-instructions.md",
        }

        for harness, target in cases.items():
            with self.subTest(harness=harness):
                self.assertIn(target, plans[harness].links)

        self.assertIn(
            self.home / ".jcode" / "skills" / "agents-contract",
            plans["jcode"].links,
        )
        self.assertIn(
            self.home / "forge" / "skills" / "agents-contract",
            plans["forge"].links,
        )
        self.assertTrue(plans["fx"].copy)
        self.assertIn(
            self.home / ".fx" / "skills" / "agents-contract",
            plans["fx"].dirs,
        )

    def test_detect_accepts_a_config_directory(self) -> None:
        (self.home / ".config" / "opencode").mkdir(parents=True)
        absent = install.HarnessSpec(
            "absent", ("definitely-not-installed-lowheat",), ".absent", ()
        )

        self.assertTrue(install.detect(install.SPEC_BY_NAME["opencode"], self.home))
        self.assertFalse(install.detect(absent, self.home))

    def test_auto_selects_only_detected_harnesses(self) -> None:
        (self.home / ".gemini").mkdir(parents=True)

        code = install.main(
            ["--home", str(self.home), "--harness", "auto", "--dry-run"]
        )

        self.assertEqual(0, code)

    def test_auto_with_no_detected_harness_reports_an_error(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(install, "detect", return_value=False):
            with contextlib.redirect_stderr(stderr):
                code = install.main(["--home", str(self.home), "--harness", "auto"])

        self.assertEqual(1, code)
        self.assertIn("no harness detected", stderr.getvalue())

    def test_user_scope_project_only_harness_reports_and_does_not_install(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(install, "sync_contract_mirror") as sync:
            with contextlib.redirect_stderr(stderr):
                code = install.main(["--home", str(self.home), "--harness", "cursor"])

        self.assertEqual(0, code)
        self.assertIn("not available in user scope", stderr.getvalue())
        self.assertFalse((self.home / ".cursor").exists())
        sync.assert_not_called()

    def test_list_harnesses_omits_detection_status(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = install.main(["--home", str(self.home), "--list-harnesses"])

        self.assertEqual(0, code)
        self.assertNotIn("detected", stdout.getvalue())
        self.assertNotIn("missing", stdout.getvalue())

    def test_detect_adds_detection_status(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = install.main(["--home", str(self.home), "--detect"])

        self.assertEqual(0, code)
        self.assertRegex(stdout.getvalue(), r"\b(detected|missing)\b")

    def test_a_missing_home_is_refused_cleanly(self) -> None:
        missing = self.home / "missing-home"
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            code = install.main(["--home", str(missing), "--harness", "claude"])

        self.assertEqual(1, code)
        self.assertIn("does not exist", stderr.getvalue())

    def test_a_file_at_the_home_path_is_refused_cleanly(self) -> None:
        home_file = self.home / "not-a-home"
        home_file.write_text("x\n", encoding="utf-8")
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            code = install.main(["--home", str(home_file), "--harness", "claude"])

        self.assertEqual(1, code)
        self.assertIn("is not a directory", stderr.getvalue())

    def test_a_file_at_a_target_parent_is_reported_not_raised(self) -> None:
        (self.home / ".claude").write_text("not a directory\n", encoding="utf-8")
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            code = install.main(["--home", str(self.home), "--harness", "claude"])

        self.assertEqual(1, code)
        self.assertIn("install:", stderr.getvalue())

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

    def test_force_replaces_a_directory_at_a_file_target(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        (root / "AGENTS.md").mkdir()
        (root / "AGENTS.md" / "keep.txt").write_text("mine\n", encoding="utf-8")

        code = install.main(
            ["--scope", "project", "--root", str(root), "--harness", "claude", "--force"]
        )

        self.assertEqual(0, code)
        self.assertTrue((root / "AGENTS.md").is_file())
        self.assertFalse((root / "AGENTS.md").is_symlink())
        self.assertFalse((root / "AGENTS.md" / "keep.txt").exists())

    def test_force_dry_run_leaves_a_directory_target_intact(self) -> None:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        (root / "AGENTS.md").mkdir()

        code = install.main(
            [
                "--scope",
                "project",
                "--root",
                str(root),
                "--harness",
                "claude",
                "--force",
                "--dry-run",
            ]
        )

        self.assertEqual(0, code)
        self.assertTrue((root / "AGENTS.md").is_dir())

    def test_force_replaces_a_real_skill_directory_without_a_backup(self) -> None:
        skill = self.home / ".claude" / "skills" / install.SKILL_DIR.name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text("MY OWN SKILL\n", encoding="utf-8")

        code = install.main(["--home", str(self.home), "--harness", "claude", "--force"])

        self.assertEqual(0, code)
        self.assertTrue(skill.is_symlink())
        self.assertFalse(skill.with_name(skill.name + ".bak").exists())

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
    def test_mirrors_generate_byte_identical_to_their_sources(self) -> None:
        skill = Path(tempfile.mkdtemp()) / "agents-contract"
        self.addCleanup(lambda: __import__("shutil").rmtree(skill.parent, ignore_errors=True))
        targets = install.sync_contract_mirror(install.CONTRACT_DIR, skill)

        self.assertEqual(
            [
                skill / "references" / "contract.md",
                skill / "references" / "codedna.md",
                skill / "references" / "commands.md",
            ],
            [path for path, _ in targets],
        )
        self.assertTrue(all(action == "wrote" for _, action in targets), targets)
        for source, (target, _) in zip(
            ("AGENTS.md", "codedna.md", "RTK.md"), targets, strict=True
        ):
            self.assertEqual((install.CONTRACT_DIR / source).read_bytes(), target.read_bytes())

    def test_checked_in_mirrors_match_their_sources(self) -> None:
        for source, mirror in (
            ("AGENTS.md", "contract.md"),
            ("codedna.md", "codedna.md"),
            ("RTK.md", "commands.md"),
        ):
            self.assertEqual(
                (install.CONTRACT_DIR / source).read_bytes(),
                (install.SKILL_DIR / "references" / mirror).read_bytes(),
                mirror,
            )

    def test_a_dry_run_writes_no_mirror_and_reports_the_action(self) -> None:
        skill = Path(tempfile.mkdtemp()) / "agents-contract"
        self.addCleanup(lambda: __import__("shutil").rmtree(skill.parent, ignore_errors=True))

        targets = install.sync_contract_mirror(install.CONTRACT_DIR, skill, dry_run=True)

        self.assertTrue(all(action == "wrote" for _, action in targets), targets)
        for path, _ in targets:
            self.assertFalse(path.exists(), path)

    def test_second_mirror_run_reports_unchanged(self) -> None:
        skill = Path(tempfile.mkdtemp()) / "agents-contract"
        self.addCleanup(lambda: __import__("shutil").rmtree(skill.parent, ignore_errors=True))
        install.sync_contract_mirror(install.CONTRACT_DIR, skill)

        targets = install.sync_contract_mirror(install.CONTRACT_DIR, skill)

        self.assertTrue(all(action == "unchanged" for _, action in targets), targets)


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
                plan.dirs,
            )
            emitted.update(unique.links)
            emitted.update(unique.dirs)
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

    def test_project_aliases_cover_non_agents_harnesses(self) -> None:
        plans = install.plan_project(self.root)

        for harness, alias in (
            ("claude", "CLAUDE.md"),
            ("gemini", "GEMINI.md"),
            ("crush", "CRUSH.md"),
            ("aider", "CONVENTIONS.md"),
            ("qwen", "QWEN.md"),
        ):
            with self.subTest(harness=harness):
                self.assertEqual(
                    install.CONTRACT_DIR / "AGENTS.md",
                    plans[harness].links[self.root / alias],
                )

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

        self.assertEqual([], list(self.home.rglob("*")))


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

    def test_force_replaces_a_foreign_agents_md_without_a_backup(self) -> None:
        agents = self.root / "AGENTS.md"
        agents.write_text("MY OWN RULES\n", encoding="utf-8")

        code = install.main(
            ["--scope", "project", "--root", str(self.root), "--force"]
        )

        self.assertEqual(0, code)
        self.assertNotEqual("MY OWN RULES\n", agents.read_text(encoding="utf-8"))
        self.assertFalse((self.root / "AGENTS.md.bak").exists())

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

    def test_project_scope_refuses_a_nested_source_checkout_root(self) -> None:
        contract = install._HERE / "contract"
        before = (contract / "AGENTS.md").read_bytes()

        code = install.main(["--scope", "project", "--root", str(contract)])

        self.assertEqual(1, code)
        self.assertEqual(before, (contract / "AGENTS.md").read_bytes())

    def test_project_scope_refuses_a_parent_of_the_checkout(self) -> None:
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            code = install.main(["--scope", "project", "--root", str(install._HERE.parent)])

        self.assertEqual(1, code)
        self.assertIn("overlaps the lowheat source checkout", stderr.getvalue())

    def test_project_scope_refuses_a_file_root_cleanly(self) -> None:
        root = Path(tempfile.mkdtemp()) / "not-a-root"
        root.write_text("x\n", encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(root.parent, ignore_errors=True))
        stderr = io.StringIO()

        with contextlib.redirect_stderr(stderr):
            code = install.main(["--scope", "project", "--root", str(root)])

        self.assertEqual(1, code)
        self.assertIn("is not a directory", stderr.getvalue())

    def apply(self) -> None:
        install.main(["--scope", "project", "--root", str(self.root)])


if __name__ == "__main__":
    unittest.main()
