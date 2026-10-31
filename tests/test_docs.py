"""test_docs.py — Guardrails for the thin contract and skill mirrors.

exports: class DocsTestCase
used_by: none
rules:   Assert structure and source-to-mirror equality without writing files. The contract must stay thin and reference companions by name rather than importing them; every reference path the skill names must exist.
agent:   fx | unknown | 2026-10-31 | unknown | added after the thin-contract restructure to catch missing companions, stale mirrors, and the return of @ imports
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


class DocsTestCase(unittest.TestCase):
    def test_contract_is_thin(self) -> None:
        text = AGENTS.read_text(encoding="utf-8")

        self.assertLess(len(text.split()), 5000)
        self.assertNotRegex(text, r"(?m)^@\S+$")

    def test_contract_has_a_version_line(self) -> None:
        first_page = AGENTS.read_text(encoding="utf-8").split("\n\n", 2)[1]

        self.assertRegex(first_page, r"^Contract-Version: \d{4}-\d{2}-\d{2}$")

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

    def test_skill_reference_paths_exist(self) -> None:
        named = set(re.findall(r"references/[\w.-]+\.md", SKILL.read_text(encoding="utf-8")))

        self.assertTrue(named)
        for name in named:
            self.assertTrue((install.SKILL_DIR / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
