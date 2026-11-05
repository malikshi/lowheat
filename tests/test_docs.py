"""test_docs.py — Guardrails for the thin contract and skill mirrors.

exports: class DocsTestCase
used_by: none
rules:   Assert structure and source-to-mirror equality without writing files. The contract must stay thin and reference companions by name rather than importing them; every reference path the skill names must exist, and the skill and contract must agree on precedence, gates, trailers, and the compliance record.
agent:   fx | unknown | 2026-10-31 | unknown | added after the thin-contract restructure to catch missing companions, stale mirrors, and the return of @ imports
agent:   fx | unknown | 2026-11-05 | unknown | pinned the session-bootstrap, RTK, and compliance-record gates in contract and skill
agent:   fx | unknown | 2026-11-05 | unknown | pinned the loop companion gates and six-companion contract
agent:   fx | unknown | 2026-11-05 | unknown | pinned the project rulebook boundary and its exclusion from installed companions
agent:   grok-4.5 | xai | 2026-11-06 | 01a1add5-9f8f-7f01-ac4b-21d24f6dceaa | pinned skill precedence, rulebook gates, rejected-attempt trailer, and local review enum
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
            "Three attempts maximum",
            "UNIT:",
            "cost to undo",
            "project-owned `RULES.md`",
            "rulebook, not",
            "contract and companions are read-only",
        ):
            self.assertIn(marker, loop)
        self.assertNotIn("drops the gist's `RULES.md`", loop)

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
        self.assertIn("MANDATORY", skill.split("---", 2)[1])

    def test_skill_reference_paths_exist(self) -> None:
        named = set(re.findall(r"references/[\w.-]+\.md", SKILL.read_text(encoding="utf-8")))

        self.assertTrue(named)
        for name in named:
            self.assertTrue((install.SKILL_DIR / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
