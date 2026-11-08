"""codedna_python.py — Python symbol and import facts for the CodeDNA checker.

exports: module_symbols | module_name | imports_of | importer_index | used_by_findings
used_by: .agents/skills/agents-contract/scripts/codedna_headers.py → module_symbols [cascade]
used_by: .agents/skills/agents-contract/scripts/codedna_check.py → imports_of, importer_index, module_name, used_by_findings [cascade]
related: codedna_headers.py owns the used_by path check; this module supplies the import graph behind it.
rules:   Parse, never execute. An unparseable file yields None from module_symbols and no imports, so the caller falls back to text scanning instead of reporting drift it cannot prove. Only the declared direction is judged — a header never has to enumerate every public name. A used_by consumer is proven by a matching module import; a relative import resolves against the consumer's own package, and no symbol-level match is attempted.
agent:   fx | unknown | 2026-11-06 | unknown | extracted the Python facts the checker was doing with regexes: ast symbol set and reverse-import graph
agent:   antigravity | google | 2026-11-07 | 36039219-77f4-44e2-9830-d1fb34127935 | scoped bare import match to siblings and case-insensitive .py check via suffix_for
"""
from __future__ import annotations

import ast
from pathlib import Path

from codedna_spec import _ARROW_SPLIT, _EXPORT_SPLIT, suffix_for


def _statements(nodes: list[ast.stmt]):
    """Yield module-level statements, descending into control flow.

    Rules:   A definition inside `if`/`try`/`with` at module scope is still public; a function body is never descended into.
    """
    for node in nodes:
        yield node
        blocks = []
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith)):
            blocks = [node.body, node.orelse]
        elif isinstance(node, ast.Try):
            blocks = [node.body, node.orelse, node.finalbody]
            blocks.extend(handler.body for handler in node.handlers)
        for block in blocks:
            yield from _statements(block)


def module_symbols(body: str) -> set[str] | None:
    """Return every name the module binds, or None when the body does not parse.

    Rules:   Definitions, imports, and assignments all count, so a module that re-exports a symbol satisfies `exports:`. Only the declared direction is judged — a hand-maintained header is never required to enumerate every constant.
    """
    try:
        tree = ast.parse(body)
    except (SyntaxError, ValueError):
        return None
    bound: set[str] = set()
    for node in _statements(tree.body):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Import):
            bound.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            bound.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if not isinstance(target, ast.Name):
                    continue
                bound.add(target.id)
    return bound


def _package_parts(path: Path, root: Path) -> list[str]:
    """Return the dotted-package parts of one file, without its name.

    Rules:   A path outside the scanned root has no package and yields an empty list.
    """
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return []
    return list(relative.parts[:-1])


def module_name(path: Path, root: Path) -> str:
    """Return the dotted module name of one Python file.

    Rules:   `__init__.py` names its package, not a module; a file outside the root has no name.
    """
    parts = _package_parts(path, root)
    if not parts and not path.resolve().is_relative_to(root.resolve()):
        return ""
    stem = path.stem
    if stem != "__init__":
        parts.append(stem)
    return ".".join(parts)


def imports_of(path: Path, root: Path) -> set[str]:
    """Return every module name one file imports, relative imports resolved.

    Rules:   `from a.b import c` contributes `a.b` — `c` may be a symbol, so it is never claimed as a module; a relative import resolves against the consumer's package and is dropped when it escapes the root.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, SyntaxError, ValueError):
        return set()
    package = _package_parts(path, root)
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            cut = len(package) - (node.level - 1)
            if cut < 0:
                continue
            base = ".".join(package[:cut])
            module = ".".join(part for part in (base, node.module or "") if part)
        else:
            module = node.module or ""
        if module:
            modules.add(module)
    return modules


def importer_index(imports: dict[Path, set[str]]) -> dict[str, set[Path]]:
    """Invert per-file imports into a module to importers map.

    Rules:   Paths are stored resolved so a relative scan path still compares equal to a resolved consumer.
    """
    index: dict[str, set[Path]] = {}
    for path, modules in imports.items():
        for module in modules:
            index.setdefault(module, set()).add(path.resolve())
    return index


def _matches(module: str, imported: str, target_path: Path, importer_path: Path) -> bool:
    """Judge whether importer_path importing `imported` targets `module`.

    Rules:   Exact match or submodule import always matches; a dotted-tail match (`module.endswith("." + imported)`) matches if importer is a sibling in the same directory, or if `imported` has package depth matching under a top-level source directory. A bare name imported from a different directory never matches.
    """
    if imported == module or imported.startswith(module + "."):
        return True
    if module.endswith("." + imported):
        if importer_path.parent == target_path.parent:
            return True
        if "." in imported:
            return True
    return False


def _importers_of(module: str, target_path: Path, index: dict[str, set[Path]]) -> set[Path]:
    """Return every file importing a module or one of its submodules."""
    found: set[Path] = set()
    for imported, paths in index.items():
        for importer in paths:
            if _matches(module, imported, target_path, importer):
                found.add(importer)
    return found


def _loads_by_importlib(path: Path) -> bool:
    """Judge a consumer that loads its dependency by file path instead of importing it.

    Rules:   An `importlib` mention exempts the consumer from the import proof only; its path is still checked. The test suite loads this checker by path, which no import graph can see.
    """
    try:
        return "importlib" in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def used_by_findings(
    path: Path, root: Path, declared: list[str], index: dict[str, set[Path]]
) -> list[str]:
    """Report used_by entries that no import backs, and importers the header omits.

    Rules:   Only Python consumers are judged, because only Python imports are parsed; a consumer outside the scanned root is left to the path check. `none` declares no consumers, so every real importer is reported.
    """
    module = module_name(path, root)
    if not module:
        return []
    findings: list[str] = []
    declared_paths: set[Path] = set()
    importers = _importers_of(module, path.resolve(), index)
    for entry in declared:
        for part in _EXPORT_SPLIT.split(entry):
            target = _ARROW_SPLIT.split(part, maxsplit=1)[0].replace("[cascade]", "").strip()
            if not target or target.lower() == "none":
                continue
            consumer = (root / target).resolve()
            if suffix_for(consumer.name) != ".py" or not consumer.is_file():
                continue
            declared_paths.add(consumer)
            if consumer == path.resolve() or consumer in importers:
                continue
            if _loads_by_importlib(consumer):
                continue
            findings.append(f"used_by consumer does not import this module: {target}")
    for importer in sorted(importers):
        if importer != path.resolve() and importer not in declared_paths:
            findings.append(
                f"used_by omits an importer: {importer.relative_to(root.resolve()).as_posix()}"
            )
    return findings
