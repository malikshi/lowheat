"""test_docs.py — Guardrails for the thin contract and skill mirrors.

exports: class DocsTestCase
used_by: none
rules:   Assert structure and source-to-mirror equality without writing files. The contract must stay thin and under the 24,000-byte per-file rule cap, reference companions by name rather than importing them; every reference path the skill names must exist, the skill and contract must agree on precedence, gates, trailers, and the compliance record, the README companion prose must name every registered companion, the review companion must pin the upstream taxonomy and reviewer-fallback gates, and its model-panel naming must dispatch catalog-printed ids while banning no alias set.
agent:   fx | unknown | 2026-11-24 | unknown | pinned README companion prose to the installer registry
agent:   fx | unknown | 2026-11-24 | unknown | pinned upstream review taxonomy and reviewer-fallback gates
agent:   gemini-4-carbon | google | 2026-11-25 | b221ee10-722e-4fa5-bcc3-ee4a6c26742f | pinned 24 KB rule cap, autonomous bootstrap/review rules, and RTK/semble/continue updates
agent:   gemini-4-neon | google | 2026-11-26 | d7bcc136-70e7-4923-8114-ec7f030fb78d | replaced delete-comment and comment_budget checks with word-only codedna audit and full 24 KB cap assertions
agent:   fx | unknown | 2026-11-26 | unknown | allowed catalog-printed bare aliases in the panel, kept the no-hard-coded-provider rule
"""

from __future__ import annotations

import importlib
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

install = importlib.import_module("install")
AGENTS = install.CONTRACT_DIR / "AGENTS.md"
SKILL = install.SKILL_DIR / "SKILL.md"
MAX_CONTRACT_WORDS = 5400
MAX_RULE_BYTES = 24_000


class DocsTestCase(unittest.TestCase):
    def test_contract_is_thin(self) -> None:
        text = AGENTS.read_text(encoding="utf-8")

        self.assertLess(len(text.split()), MAX_CONTRACT_WORDS)
        self.assertNotRegex(text, r"(?m)^@\S+$")

    def test_contract_and_companions_fit_24kb_rule_cap(self) -> None:
        paths = (
            AGENTS,
            *(install.CONTRACT_DIR / name for name in install.COMPANIONS),
            install.CONTRACT_DIR / "continue.md",
            *sorted(install.AGENTS_DIR.glob("*.md")),
            SKILL,
        )
        for path in paths:
            with self.subTest(path=path.name):
                self.assertLessEqual(len(path.read_bytes()), MAX_RULE_BYTES)

    def test_contract_has_a_version_line(self) -> None:
        first_page = AGENTS.read_text(encoding="utf-8").split("\n\n", 2)[1]

        self.assertRegex(first_page, r"^Contract-Version: \d{4}-\d{2}-\d{2}\.\d+$")

    def test_every_companion_exists_and_is_named(self) -> None:
        text = AGENTS.read_text(encoding="utf-8")

        for name in install.COMPANIONS:
            self.assertTrue((install.CONTRACT_DIR / name).is_file(), name)
            self.assertIn(name, text)

    def test_skill_mirrors_match_their_sources(self) -> None:
        pairs = (
            (AGENTS, install.SKILL_DIR / "references" / "contract.md"),
            (
                install.CONTRACT_DIR / "codedna.md",
                install.SKILL_DIR / "references" / "codedna.md",
            ),
            (
                install.CONTRACT_DIR / "RTK.md",
                install.SKILL_DIR / "references" / "commands.md",
            ),
        )

        for source, mirror in pairs:
            self.assertEqual(source.read_bytes(), mirror.read_bytes(), mirror)

    def test_loop_companion_pins_the_unit_gates(self) -> None:
        loop = (install.CONTRACT_DIR / "loop.md").read_text(encoding="utf-8")

        for marker in (
            "Step 0",
            "Work Loop 1",
            "Work Loop 2–3",
            "CodeDNA headers",
            "Three attempts maximum",
            "pre-unit state",
            "fresh three-attempt budget",
            "5 Merge, then review",
            "UNIT:",
            "cost to undo",
            "project-owned `RULES.md`",
            "rulebook, not",
            "contract and companions are read-only",
        ):
            self.assertIn(marker, loop)
        self.assertNotIn("drops the gist's `RULES.md`", loop)
        self.assertNotIn("5 Self-review", loop)

    def test_project_rulebook_is_documented_but_not_installed(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        codedna = (install.CONTRACT_DIR / "codedna.md").read_text(encoding="utf-8")
        readme = (install.CONTRACT_DIR.parent / "README.md").read_text(encoding="utf-8")

        for marker in (
            "project-owned `RULES.md`",
            "installed contract copy",
            "The project's `RULES.md`, when present",
        ):
            self.assertIn(marker, contract)
        self.assertIn("rulebook, not a session ledger", codedna)
        self.assertIn("never installed by lowheat", readme)
        self.assertNotIn("RULES.md", install.COMPANIONS)

    def test_skill_and_contract_agree_on_precedence(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        self.assertIn("The project's `RULES.md`, when present", contract)
        self.assertIn("then the project's `RULES.md`", skill)
        self.assertIn("never relaxes the approval gates", skill)
        self.assertIn("It narrows this file; it never", contract)
        self.assertIn("relaxes the gates below", contract)

    def test_rulebook_gates_and_version_policy_are_pinned(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        readme = (install.CONTRACT_DIR.parent / "README.md").read_text(encoding="utf-8")

        self.assertIn("These gates hold whatever a project `RULES.md` says", contract)
        self.assertIn("approval before a commit or push", contract)
        self.assertIn("bump `N` for every change to any installed surface", contract)
        self.assertIn("never relaxes the approval", readme)

    def test_rejected_attempts_have_a_trailer(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        loop = (install.CONTRACT_DIR / "loop.md").read_text(encoding="utf-8")

        for text in (contract, skill):
            self.assertIn("AI-Rejected:", text)
        self.assertIn("`AI-Rejected:`", loop)

    def test_compliance_record_covers_local_reviews(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        for text in (contract, skill):
            self.assertIn("not required (small or local, no STOP trigger)", text)

    def test_direct_download_loops_match_installer_companions(self) -> None:
        readme = (install.CONTRACT_DIR.parent / "README.md").read_text(encoding="utf-8")
        loops = re.findall(r"^for f in ([^;]+); do$", readme, re.MULTILINE)

        self.assertEqual(2, len(loops))
        first, second = loops
        self.assertEqual(("AGENTS.md",) + install.COMPANIONS, tuple(first.split()))
        self.assertEqual(install.COMPANIONS, tuple(second.split()))
        self.assertNotIn("six companions", readme)

    def test_companion_prose_names_every_companion(self) -> None:
        readme = (install.CONTRACT_DIR.parent / "README.md").read_text(encoding="utf-8")
        prose = re.search(
            r"^The companions hold the detail.*?(?=\n\n)", readme, re.MULTILINE | re.DOTALL
        )

        self.assertIsNotNone(prose)
        for name in install.COMPANIONS:
            with self.subTest(name=name):
                self.assertIn(f"`{name}`", prose.group())

    def test_review_companion_pins_upstream_taxonomy_and_reviewer_fallback(self) -> None:
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")
        contract = AGENTS.read_text(encoding="utf-8")

        for marker in (
            "Authority reconciliation",
            "Identity and correlation",
            "Representation and information loss",
            "nullish",
            "field-set drift",
            "Unresolved values stored as resolved",
            "Verification and observability",
            "Deduplicate by violated agreement and root cause",
            "subagent of the harness you are",
            "no second",
            "installed `reviewer`",
            "must not inherit the builder's beliefs",
            "fresh session of the builder's",
            "cannot rule out a review",
            "Name the actual reviewer",
            "recorded fallback",
            "usage model",
            "literal triggering sequence",
            "Question zero",
            "costs this product",
            "fix that did not need to happen is itself",
            "Before the first release",
            "Split by contiguous commits or by complete",
            "by surface when it does not",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, review)
        self.assertIn("Never skip", contract)

    def test_review_companion_pins_both_engines(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")

        self.assertIn("review.md", install.COMPANIONS)
        self.assertIn("`review.md`", contract)
        self.assertIn("`review.md`", skill)
        for marker in (
            "agreement engine",
            "five elements",
            "feasible execution",
            "observable consequence",
            "counterargument",
            "Coverage:",
            "fresh subagent",
            "never saw the build",
            "read-only",
            "no INTRODUCED finding above Low",
            "Rerun the tests a fix touches",
            "INTRODUCED",
            "pre-existing",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, review)

    def test_review_agents_ship_as_subagent_definitions(self) -> None:
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")
        contract = AGENTS.read_text(encoding="utf-8")
        names = {path.stem for path in install.AGENTS_DIR.glob("*.md")}

        self.assertEqual({"reviewer", "review-finder"}, names)
        for path in install.AGENTS_DIR.glob("*.md"):
            rendered = install.render_agent(path)
            header, body = rendered.split("---")[1], rendered.split("---", 2)[2]
            with self.subTest(agent=path.name):
                self.assertIn(f"name: {path.stem}", header)
                self.assertIn("description:", header)
                self.assertIn("Read-only", body)
                self.assertNotIn("Edit", header)
        self.assertIn("`reviewer`", contract)
        self.assertIn("`review-finder`", contract)
        self.assertIn("installed definition", contract)
        self.assertIn("review-finder", review)
        self.assertNotIn("headless", contract)
        self.assertNotIn("headless", review)

    def test_the_installed_contract_does_not_point_at_repo_internal_paths(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")
        codedna = (install.CONTRACT_DIR / "codedna.md").read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        for name, text in (
            ("AGENTS.md", contract),
            ("review.md", review),
            ("codedna.md", codedna),
            ("SKILL.md", skill),
        ):
            for internal in ("contract/agents", "source repository"):
                with self.subTest(file=name, internal=internal):
                    self.assertNotIn(internal, text)
        self.assertNotIn("install.py", review)
        self.assertNotIn("this repository, `.agents/skills", contract)
        self.assertIn("installed beside this contract", contract)

    def test_review_companion_pins_the_model_panel(self) -> None:
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        for marker in (
            "### Model panel",
            "byte-identical",
            "Members never see each other",
            "A panel is one round, not three",
            "not by counting votes",
            "A model that\nreturns nothing usable is a failed member",
            "It\napplies to both subagents",
            "every flow still gets every\nmodel",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, review)
        self.assertIn("Model panel", contract)
        self.assertIn("Model panel", skill)
        self.assertIn("either\nsubagent's body", contract)
        self.assertIn("`review-finder` body plus", skill)

    def test_a_panel_prompt_carries_the_definition_body_for_both_agents(self) -> None:
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")

        self.assertIn("that agent's full\ndefinition body", review)
        self.assertIn("for `review-finder` it names the flow", review)
        self.assertIn("**Naming the models.**", review)
        self.assertIn("Pick one provider that the session can already reach", review)
        self.assertIn("Name each id as the catalog prints it", review)
        self.assertNotIn("the `reviewer` body plus", review)

    def test_panel_naming_dispatches_catalog_ids_and_bans_no_alias_set(self) -> None:
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")

        self.assertIn("Do not hard-code a provider", review)
        self.assertNotIn("personal aliases", review)
        self.assertIn("bare alias when it prints bare", review)
        self.assertIn("qualify it with the provider prefix or drop", review)
        self.assertIn("Where the catalog serves them, prefer `opus-model`, `sonnet-model`, and", review)
        self.assertIn("a name the catalog\ndoes not serve is not a member", review)
        self.assertIn("That is a default, not a privilege", review)
        self.assertIn("swap one member out", review)
        self.assertIn("say the panel spans two families", review)
        for private in ("nexrouter", "9router", "127.0.0.1", "baseURL"):
            with self.subTest(private=private):
                self.assertNotIn(private, review)

    def test_a_pinned_model_in_the_definition_would_collapse_the_panel(self) -> None:
        for path in install.AGENTS_DIR.glob("*.md"):
            fields = install.render_agent(path).split("---")[1]
            with self.subTest(agent=path.name):
                self.assertNotIn("model:", fields)

    def test_agent_rendering_matches_each_harness_shape(self) -> None:
        source = install.AGENTS_DIR / "reviewer.md"

        claude = install.render_agent(source, "claude")
        self.assertIn("tools: Bash, Read, Grep, Glob", claude.split("---")[1])
        self.assertIn("mode: subagent", install.render_agent(source, "opencode"))
        self.assertIn("readonly: true", install.render_agent(source, "grok").split("---")[1])
        self.assertIn(
            "  - run_shell_command", install.render_agent(source, "gemini").split("---")[1]
        )
        codex = install.render_agent(source, "codex")
        self.assertTrue(codex.startswith('name = "reviewer"\n'))
        self.assertIn('sandbox_mode = "read-only"', codex)
        self.assertIn("developer_instructions = '''", codex)
        self.assertEqual(
            {"reviewer.toml", "review-finder.toml"},
            set(install.render_agents(install.SPEC_BY_NAME["codex"], install.AGENTS_DIR)),
        )
        self.assertEqual({}, install.render_agents(install.SPEC_BY_NAME["pi"], install.AGENTS_DIR))

    def test_a_malformed_agent_file_is_refused(self) -> None:
        cases = {
            "no-block.md": "name: reviewer\n",
            "unclosed.md": "---\nname: reviewer\n",
            "nameless.md": "---\ndescription: no name here\n---\nbody\n",
        }

        for filename, text in cases.items():
            path = Path(self._tmp()) / filename
            path.write_text(text, encoding="utf-8")
            with self.subTest(filename=filename):
                with self.assertRaises(ValueError):
                    install.render_agent(path)

    def test_codex_render_survives_quotes_in_frontmatter(self) -> None:
        import tomllib

        path = Path(self._tmp()) / "quoted.md"
        path.write_text(
            '---\nname: reviewer\ndescription: has "quotes" and a \\ backslash\n---\nbody\n',
            encoding="utf-8",
        )

        data = tomllib.loads(install.render_agent(path, "codex"))
        self.assertEqual("reviewer", data["name"])
        self.assertIn('"quotes"', data["description"])
        self.assertEqual("body\n", data["developer_instructions"])

    def test_a_body_that_breaks_codex_toml_is_refused(self) -> None:
        path = Path(self._tmp()) / "triple.md"
        path.write_text("---\nname: reviewer\n---\nUse ''' fences.\n", encoding="utf-8")

        self.assertIn("Use", install.render_agent(path, "claude"))
        with self.assertRaises(ValueError):
            install.render_agent(path, "codex")

    def test_a_body_with_double_quotes_is_fine_in_codex(self) -> None:
        path = Path(self._tmp()) / "dquotes.md"
        path.write_text('---\nname: reviewer\n---\nUse """ fences.\n', encoding="utf-8")

        self.assertIn("USE", install.render_agent(path, "codex").upper())

    def test_every_rendered_agent_parses_in_its_own_format(self) -> None:
        import tomllib

        for path in install.AGENTS_DIR.glob("*.md"):
            with self.subTest(agent=path.name):
                codex = tomllib.loads(install.render_agent(path, "codex"))
                self.assertEqual("read-only", codex["sandbox_mode"])
                self.assertTrue(codex["developer_instructions"].strip())
                header = install.render_agent(path, "claude").split("---")[1]
                self.assertIn(f"name: {path.stem}", header)

    def _tmp(self) -> str:
        import tempfile

        directory = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(directory, ignore_errors=True))
        return directory

    def test_review_standards_point_to_the_companion(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        for text in (contract, skill):
            self.assertIn("agreement", text)
            self.assertIn("fresh", text)
            self.assertIn("refut", text)

    def test_codedna_checker_is_documented(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        codedna = (install.CONTRACT_DIR / "codedna.md").read_text(encoding="utf-8")
        mirror = (install.SKILL_DIR / "references" / "codedna.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("skill ships its own read-only checker", contract)
        for text in (codedna, mirror):
            self.assertIn("read-only checker", text)
        self.assertNotIn("There is no binary, validator", contract)

    def test_comment_audit_categories_and_homes_are_pinned(self) -> None:
        codedna = (install.CONTRACT_DIR / "codedna.md").read_text(encoding="utf-8")
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")
        root = install.CONTRACT_DIR.parent

        labels = ("Tautology", "Excuse", "Stale", "Decision Record")
        for label in labels:
            with self.subTest(label=label):
                self.assertIn(label, codedna)
                self.assertIn(label, contract)
                self.assertIn(label, skill)
        for name, text in (("codedna.md", codedna), ("AGENTS.md", contract), ("SKILL.md", skill)):
            audit = text.split("Comment audit", 1)[1]
            positions = [audit.index(label) for label in labels]
            with self.subTest(order_in=name):
                self.assertEqual(sorted(positions), positions)
        for marker in (
            "docs/adr/",
            "docs/comment-debt.md",
            "earlier one",
            "**same** change",
            "Grading examples",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, codedna)
        for retired in (
            "comment_budget.py",
            "comment-budget.json",
            "delete-comment",
            "budget script",
            "shrinking or flat",
        ):
            for name, text in (("AGENTS.md", contract), ("codedna.md", codedna), ("SKILL.md", skill)):
                with self.subTest(retired=retired, file=name):
                    self.assertNotIn(retired, text)
        self.assertFalse((root / ".github" / "workflows" / "ci.yml").exists())
        self.assertFalse((install.SKILLS_DIR / "delete-comment").exists())
        self.assertFalse((install.SKILL_DIR / "scripts" / "comment_budget.py").exists())
        self.assertFalse((root / "docs" / "comment-budget.json").exists())
        self.assertFalse((root / "docs" / "comment-debt.md").exists())
        self.assertTrue((root / "docs" / "adr" / "README.md").is_file())
        self.assertTrue((root / "docs" / "adr" / "0000-template.md").is_file())
        self.assertTrue((root / "docs" / "adr" / "0001-comments-are-codedna-only.md").is_file())
        self.assertTrue((root / "docs" / "adr" / "0002-comment-audit-is-prose-in-codedna.md").is_file())

    def test_commit_format_accepts_an_optional_scope(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        for text in (contract, skill):
            self.assertIn("<type>(<scope>): <description>", text)
        self.assertIn("The scope is optional", contract)
        self.assertIn("the scope is optional", skill)

    def test_contract_and_skill_carry_bootstrap_gates(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        for marker in ("Session bootstrap", "RTK gate", "Compliance record"):
            self.assertIn(marker, contract)
        for marker in ("Startup gate", "RTK gate", "Compliance record"):
            self.assertIn(marker, skill)
        self.assertIn("before any task tool call", contract)
        self.assertIn("before any task tool call", skill)
        self.assertIn("functions or blocks you edit", contract)
        self.assertIn("path-dynamic or privileged file system operations", contract)
        self.assertIn("MANDATORY", skill.split("---", 2)[1])

    def test_skill_reference_paths_exist(self) -> None:
        named = set(re.findall(r"references/[\w.-]+\.md", SKILL.read_text(encoding="utf-8")))

        self.assertTrue(named)
        for name in named:
            self.assertTrue((install.SKILL_DIR / name).is_file(), name)

    def test_contract_and_skill_enable_autonomous_execution(self) -> None:
        contract = AGENTS.read_text(encoding="utf-8")
        skill = SKILL.read_text(encoding="utf-8")

        for text in (contract, skill):
            self.assertIn("Do not end Turn 1", text)
            self.assertIn("never block waiting for a human", text.lower())
            self.assertIn("author/coordinator", text)
        self.assertIn("Execute end-to-end without pausing", contract)

    def test_reviewer_resolves_base_without_empty_released_bug(self) -> None:
        review = (install.CONTRACT_DIR / "review.md").read_text(encoding="utf-8")
        reviewer = (install.AGENTS_DIR / "reviewer.md").read_text(encoding="utf-8")

        self.assertNotIn("--subject HEAD", review)
        self.assertIn("HEAD..HEAD", review)
        self.assertIn("HEAD..HEAD", reviewer)
        self.assertIn("define_subagent", review)
        self.assertIn("Review: unavailable", review)

    def test_rtk_and_continue_avoid_autonomous_traps(self) -> None:
        rtk = (install.CONTRACT_DIR / "RTK.md").read_text(encoding="utf-8")
        semble = (install.CONTRACT_DIR / "semble.md").read_text(encoding="utf-8")
        cont = (install.CONTRACT_DIR / "continue.md").read_text(encoding="utf-8")

        self.assertIn("1.2.1", rtk)
        self.assertIn("rtk gain --text", rtk)
        self.assertIn("0.7.3", semble)
        self.assertNotIn("and the companion files it names", cont)
        self.assertIn("only the companion files the current task needs", cont)


if __name__ == "__main__":
    unittest.main()
