from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Dict, Iterable, Optional, Set, Tuple

try:
    from .backend_utils import module_to_path
    from .graph import Graph
except ImportError:  # pragma: no cover - fallback for direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.code_map.backend_utils import module_to_path
    from scripts.code_map.graph import Graph

REPO_MODULES = ("skillmeat.cache.repositories", "skillmeat.cache.repository")
SERVICE_ROOTS = ("services", "core")


def iter_service_files(api_root: Path) -> Iterable[Path]:
    for root in SERVICE_ROOTS:
        path = api_root.parent / root
        if path.exists():
            yield from path.rglob("*.py")
    services_root = api_root / "services"
    if services_root.exists():
        yield from services_root.rglob("*.py")


def parse_imports(tree: ast.AST) -> Dict[str, str]:
    imports: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.startswith(REPO_MODULES):
                for alias in node.names:
                    name = alias.asname or alias.name
                    imports[name] = module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                if module.startswith(REPO_MODULES):
                    name = alias.asname or alias.name.split(".")[-1]
                    imports[name] = module
    return imports


def repo_node_id(module: str, name: str) -> str:
    repo_path = module_to_path(module)
    if repo_path:
        return f"repository:{repo_path.as_posix()}::{name}"
    return f"repository:{module}::{name}"


def service_node_id(path: Path, name: str) -> str:
    return f"service:{path.as_posix()}::{name}"


def extract_backend_services(api_root: Path) -> Graph:
    graph = Graph(source="backend")

    for service_file in iter_service_files(api_root):
        text = service_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue

        repo_imports = parse_imports(tree)

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                graph.add_node(
                    service_node_id(service_file, name),
                    "service",
                    label=name,
                    file=service_file.as_posix(),
                    line=node.lineno,
                    symbol=name,
                )

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                service_name = node.name
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        target_name = None
                        if isinstance(child.func, ast.Name):
                            target_name = child.func.id
                        elif isinstance(child.func, ast.Attribute) and isinstance(
                            child.func.value, ast.Name
                        ):
                            target_name = child.func.value.id
                        if not target_name:
                            continue
                        module = repo_imports.get(target_name)
                        if not module and target_name.endswith("Repository"):
                            module = REPO_MODULES[0]
                        if not module:
                            continue
                        graph.add_node(
                            repo_node_id(module, target_name),
                            "repository",
                            label=target_name,
                            file=(module_to_path(module) or service_file).as_posix(),
                        )
                        graph.add_edge(
                            service_node_id(service_file, service_name),
                            repo_node_id(module, target_name),
                            "service_calls_repository",
                        )

    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract backend service and repository usage.")
    parser.add_argument(
        "--api-root",
        default="skillmeat/api",
        help="Path to API root (default: skillmeat/api)",
    )
    parser.add_argument(
        "--out",
        default="docs/architecture/codebase-graph.backend.services.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    graph = extract_backend_services(Path(args.api_root))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    graph.write_json(args.out)


if __name__ == "__main__":
    main()
