from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

try:
    from .graph import Graph
except ImportError:  # pragma: no cover - fallback for direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.code_map.graph import Graph

MIGRATION_REVISION_RE = re.compile(r"^revision\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
CREATE_TABLE_RE = re.compile(r"create_table\(\s*['\"]([^'\"]+)['\"]")


def iter_schema_files(api_root: Path) -> Iterable[Path]:
    schemas_root = api_root / "schemas"
    if schemas_root.exists():
        yield from schemas_root.rglob("*.py")


def iter_migration_files(cache_root: Path) -> Iterable[Path]:
    migrations_root = cache_root / "migrations" / "versions"
    if migrations_root.exists():
        yield from migrations_root.rglob("*.py")


def parse_schema_classes(path: Path) -> Dict[str, int]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    classes: Dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes[node.name] = node.lineno
    return classes


def parse_models(path: Path) -> Dict[str, Tuple[int, Optional[str]]]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    models: Dict[str, Tuple[int, Optional[str]]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        table_name = None
        for stmt in node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(stmt.value, ast.Constant) and isinstance(
                            stmt.value.value, str
                        ):
                            table_name = stmt.value.value
        models[node.name] = (node.lineno, table_name)
    return models


def parse_repository_models(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    repo_models: Dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            if isinstance(base, ast.Subscript):
                if isinstance(base.value, ast.Name) and base.value.id.endswith("Repository"):
                    if isinstance(base.slice, ast.Name):
                        repo_models[node.name] = base.slice.id
                if isinstance(base.value, ast.Attribute) and base.value.attr.endswith("Repository"):
                    if isinstance(base.slice, ast.Name):
                        repo_models[node.name] = base.slice.id
            if isinstance(base, ast.Name) and base.id.endswith("Repository"):
                repo_models.setdefault(node.name, "")
    return repo_models


def migration_info(path: Path) -> Tuple[Optional[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    revision_match = MIGRATION_REVISION_RE.search(text)
    revision = revision_match.group(1) if revision_match else None
    tables = CREATE_TABLE_RE.findall(text)
    return revision, tables


def extract_backend_models(repo_root: Path) -> Graph:
    graph = Graph(source="backend")
    api_root = repo_root / "skillmeat" / "api"
    cache_root = repo_root / "skillmeat" / "cache"

    for schema_file in iter_schema_files(api_root):
        classes = parse_schema_classes(schema_file)
        for name, line in classes.items():
            graph.add_node(
                f"schema:{schema_file.as_posix()}::{name}",
                "schema",
                label=name,
                file=schema_file.as_posix(),
                line=line,
                symbol=name,
            )

    models_path = cache_root / "models.py"
    model_tables: Dict[str, Optional[str]] = {}
    if models_path.exists():
        models = parse_models(models_path)
        for name, (line, table_name) in models.items():
            model_tables[name] = table_name
            graph.add_node(
                f"model:{models_path.as_posix()}::{name}",
                "model",
                label=name,
                file=models_path.as_posix(),
                line=line,
                table=table_name,
            )

    repo_paths = [cache_root / "repositories.py", cache_root / "repository.py"]
    for repo_path in repo_paths:
        if not repo_path.exists():
            continue
        repo_models = parse_repository_models(repo_path)
        for repo_name, model_name in repo_models.items():
            repo_id = f"repository:{repo_path.as_posix()}::{repo_name}"
            graph.add_node(
                repo_id,
                "repository",
                label=repo_name,
                file=repo_path.as_posix(),
            )
            if model_name:
                model_id = f"model:{models_path.as_posix()}::{model_name}"
                graph.add_node(
                    model_id,
                    "model",
                    label=model_name,
                    file=models_path.as_posix(),
                )
                graph.add_edge(repo_id, model_id, "repository_uses_model")

    migration_tables: Dict[str, list[str]] = {}
    for migration_file in iter_migration_files(cache_root):
        revision, tables = migration_info(migration_file)
        revision_id = revision or migration_file.stem
        migration_id = f"migration:{migration_file.as_posix()}::{revision_id}"
        graph.add_node(
            migration_id,
            "migration",
            label=revision_id,
            file=migration_file.as_posix(),
        )
        if tables:
            migration_tables[migration_id] = tables

    if model_tables and migration_tables:
        for model_name, table_name in model_tables.items():
            if not table_name:
                continue
            model_id = f"model:{models_path.as_posix()}::{model_name}"
            for migration_id, tables in migration_tables.items():
                if table_name in tables:
                    graph.add_edge(model_id, migration_id, "model_migrated_by")

    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract backend schema/model/migration graph.")
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root (default: .)",
    )
    parser.add_argument(
        "--out",
        default="docs/architecture/codebase-graph.backend.models.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    graph = extract_backend_models(Path(args.repo_root).resolve())
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    graph.write_json(args.out)


if __name__ == "__main__":
    main()
