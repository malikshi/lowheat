"""test_docs.py — Guardrails for the thin contract and skill mirrors.

exports: class DocsTestCase
used_by: none
rules:   Assert structure and source-to-mirror equality without writing files. The contract must stay thin and reference companions by name rather than importing them; every reference path the skill names must exist, the skill and contract must agree on precedence, gates, trailers, and the compliance record, the README companion prose must name every registered companion, and the review companion must pin the upstream taxonomy and reviewer-fallback gates.
agent:   grok-4.5 | xai | 2026-11-06 | 01a1add5-9f8f-7f01-ac4b-21d24f6dceaa | pinned skill precedence, rulebook gates, rejected-attempt trailer, and local review enum
agent:   gemini-4-argon | google | 2026-11-08 | d7c52693-a719-48d1-a0fd-1ef0caadf691 | pinned bootstrap tool-call ordering, loop Work Loop mapping and revert/retry rules, and scoped comment/STOP gates
agent:   fx | unknown | 2026-11-23 | unknown | pinned review-companion engines, independent-round isolation, and finding triage gates
agent:   fx | unknown | 2026-11-24 | unknown | pinned README companion prose to the installer registry
agent:   fx | unknown | 2026-11-24 | unknown | pinned upstream review taxonomy and reviewer-fallback gates
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


class DocsTestCase(unittest.TestCase):
    def test_contract_is_thin(self) -> None:
        text = AGENTS.read_text(encoding="utf-8")

        self.assertLess(len(text.split()), MAX_CONTRACT_WORDS)
        self.assertNotRegex(text, r"(?m)^@\S+$")

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
            "first installed of Codex, headless Claude Code and Grok",
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
            "fresh session",
            "never saw the build",
            "read-only",
            "no INTRODUCED finding above Low",
            "Rerun the tests a fix touches",
            "INTRODUCED",
            "pre-existing",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, review)

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
        skill = (install.SKILL_DIR.parent / "delete-comment" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        root = install.CONTRACT_DIR.parent

        for label in ("Tautology", "Excuse", "Stale", "Decision Record"):
            with self.subTest(label=label):
                self.assertIn(label, codedna)
                self.assertIn(label, skill)
        self.assertIn("docs/adr/", codedna)
        self.assertIn("docs/comment-debt.md", codedna)
        self.assertIn("comment_budget.py", contract)
        self.assertIn("never raise it", contract)
        self.assertIn("--bootstrap", codedna)
        self.assertIn("--bootstrap", skill)
        self.assertIn("--template-dir", skill)
        self.assertTrue((root / "docs" / "adr" / "README.md").is_file())
        self.assertTrue((root / "docs" / "adr" / "0000-template.md").is_file())
        self.assertTrue((root / "docs" / "adr" / "0001-comments-are-codedna-only.md").is_file())
        self.assertTrue((root / "docs" / "comment-debt.md").is_file())
        self.assertTrue((root / "docs" / "comment-budget.json").is_file())

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


if __name__ == "__main__":
    unittest.main()
