from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

IMPORT_FROM_RE = re.compile(
    r"import\s+([^;]+?)\s+from\s+['\"]([^'\"]+)['\"]",
    re.DOTALL,
)
NAMED_IMPORT_RE = re.compile(r"\{([^}]+)\}")


def iter_ts_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    for suffix in ("*.ts", "*.tsx"):
        yield from root.rglob(suffix)


def parse_imported_names(clause: str) -> List[str]:
    clause = clause.strip()
    if not clause:
        return []
    if clause.startswith("type "):
        clause = clause[len("type ") :].lstrip()
    if clause.startswith("*"):
        return []
    names: List[str] = []
    named_part = ""
    if "{" in clause:
        before, after = clause.split("{", 1)
        before = before.strip().rstrip(",")
        if before:
            names.append(before)
        named_part = "{" + after
    else:
        names.append(clause.split(",")[0].strip())
        return [name for name in names if name]

    match = NAMED_IMPORT_RE.search(named_part)
    if not match:
        return [name for name in names if name]
    inside = match.group(1)
    for item in inside.split(","):
        item = item.strip()
        if not item:
            continue
        if " as " in item:
            local_name = item.split(" as ")[-1].strip()
        else:
            local_name = item
        if local_name:
            names.append(local_name)
    return [name for name in names if name]


def parse_imports(text: str) -> List[Tuple[List[str], str]]:
    imports: List[Tuple[List[str], str]] = []
    for match in IMPORT_FROM_RE.finditer(text):
        clause = match.group(1)
        module = match.group(2)
        names = parse_imported_names(clause)
        imports.append((names, module))
    return imports


def resolve_module_path(
    web_root: Path,
    current_file: Path,
    module: str,
) -> Optional[Path]:
    if module.startswith("@/"):
        base = web_root / module[2:]
    elif module.startswith("."):
        base = current_file.parent / module
    else:
        return None

    if base.suffix in (".ts", ".tsx") and base.exists():
        return base

    for suffix in (".ts", ".tsx"):
        candidate = base.with_suffix(suffix)
        if candidate.exists():
            return candidate

    if base.exists() and base.is_dir():
        for suffix in (".ts", ".tsx"):
            candidate = base / f"index{suffix}"
            if candidate.exists():
                return candidate
    return None


def is_component_name(name: str) -> bool:
    return bool(name) and name[0].isupper()


def normalize_literal(value: str) -> str:
    return " ".join(value.strip().split())


def to_pascal_case(value: str) -> str:
    parts = re.split(r"[-_\s]+", value)
    return "".join(part.capitalize() for part in parts if part)
