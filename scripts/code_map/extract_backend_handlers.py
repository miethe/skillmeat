from __future__ import annotations

import argparse
import ast
import re
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

try:
    from .backend_utils import module_to_path, resolve_relative_module
    from .graph import Graph
except ImportError:  # pragma: no cover - fallback for direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.code_map.backend_utils import module_to_path, resolve_relative_module
    from scripts.code_map.graph import Graph

ROUTER_ASSIGN_RE = re.compile(
    r"(?P<name>\w+)\s*=\s*APIRouter\((?P<args>.*?)\)",
    re.DOTALL,
)
PREFIX_RE = re.compile(r"prefix\s*=\s*['\"]([^'\"]+)['\"]")
DECORATOR_RE = re.compile(
    r"@(?P<router>\w+)\.(?P<method>get|post|put|patch|delete|options|head)\((?P<args>.*?)\)",
    re.DOTALL,
)
APP_DECORATOR_RE = re.compile(
    r"@app\.(?P<method>get|post|put|patch|delete|options|head)\((?P<args>.*?)\)",
    re.DOTALL,
)
STRING_RE = re.compile(r"['\"]([^'\"]*)['\"]")
DEF_RE = re.compile(r"(?m)^(?:async\s+def|def)\s+([A-Za-z0-9_]+)\b")

SERVICE_PREFIXES = ("skillmeat.api.services", "skillmeat.core")
SCHEMA_PREFIX = "skillmeat.api.schemas"


def parse_router_prefixes(text: str) -> Dict[str, str]:
    prefixes: Dict[str, str] = {}
    for match in ROUTER_ASSIGN_RE.finditer(text):
        name = match.group("name")
        args = match.group("args")
        prefix_match = PREFIX_RE.search(args)
        if prefix_match:
            prefixes[name] = prefix_match.group(1)
    return prefixes


def join_paths(prefix: str, path: str) -> str:
    if not prefix:
        return path
    if not path:
        return prefix
    if prefix.endswith("/") and path.startswith("/"):
        return prefix[:-1] + path
    if not prefix.endswith("/") and not path.startswith("/"):
        return prefix + "/" + path
    return prefix + path


def apply_api_prefix(api_prefix: Optional[str], path: str) -> str:
    if not api_prefix:
        return path
    api_prefix = api_prefix.rstrip("/")
    return join_paths(api_prefix, path)


def normalize_path_params(path: str) -> str:
    return re.sub(r"\{([^}:]+):[^}]+\}", r"{\1}", path)


def resolve_app_path(raw_path: str, api_prefix: Optional[str]) -> str:
    if "{settings.api_prefix}" in raw_path and api_prefix:
        return raw_path.replace("{settings.api_prefix}", api_prefix)
    return raw_path


def find_next_handler(text: str, start: int) -> Optional[str]:
    match = DEF_RE.search(text, start)
    if not match:
        return None
    return match.group(1)


def parse_imports(tree: ast.AST, file_path: Path) -> Tuple[Dict[str, str], Dict[str, str]]:
    services: Dict[str, str] = {}
    schemas: Dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            module_path = resolve_relative_module(file_path, module) or module_to_path(module)
            for alias in node.names:
                name = alias.asname or alias.name
                if module.startswith(SCHEMA_PREFIX):
                    schemas[name] = module
                if module.startswith(SERVICE_PREFIXES):
                    services[name] = module
                if module_path and module_path.as_posix().startswith("skillmeat/api/schemas"):
                    schemas[name] = module
        elif isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name
                name = alias.asname or alias.name.split(".")[-1]
                if module.startswith(SERVICE_PREFIXES):
                    services[name] = module
                if module.startswith(SCHEMA_PREFIX):
                    schemas[name] = module
    return services, schemas


def extract_annotation_names(node: Optional[ast.AST]) -> Set[str]:
    if node is None:
        return set()
    if isinstance(node, ast.Name):
        return {node.id}
    if isinstance(node, ast.Attribute):
        return {node.attr}
    if isinstance(node, ast.Subscript):
        names = set()
        names.update(extract_annotation_names(node.value))
        names.update(extract_annotation_names(node.slice))
        return names
    if isinstance(node, (ast.Tuple, ast.List)):
        names = set()
        for elt in node.elts:
            names.update(extract_annotation_names(elt))
        return names
    if isinstance(node, ast.BinOp):
        names = set()
        names.update(extract_annotation_names(node.left))
        names.update(extract_annotation_names(node.right))
        return names
    return set()


def handler_node_id(file_path: Path, name: str) -> str:
    return f"handler:{file_path.as_posix()}::{name}"


def service_node_id(module: str, name: str) -> str:
    service_path = module_to_path(module)
    if service_path:
        return f"service:{service_path.as_posix()}::{name}"
    return f"service:{module}::{name}"


def schema_node_id(module: str, name: str) -> str:
    schema_path = module_to_path(module)
    if schema_path:
        return f"schema:{schema_path.as_posix()}::{name}"
    return f"schema:{module}::{name}"


def extract_backend_handlers(api_root: Path, api_prefix: Optional[str] = None) -> Graph:
    routers_root = api_root / "routers"
    graph = Graph(source="backend")

    if api_prefix is None:
        try:
            from skillmeat.api.config import get_settings
        except Exception:
            api_prefix = ""
        else:
            api_prefix = get_settings().api_prefix

    for router_file in routers_root.rglob("*.py"):
        text = router_file.read_text(encoding="utf-8")
        prefixes = parse_router_prefixes(text)
        apply_prefix = router_file.name != "health.py"

        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = ast.parse("")

        func_defs: Dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_defs[node.name] = node

        service_imports, schema_imports = parse_imports(tree, router_file)

        for match in DECORATOR_RE.finditer(text):
            router_name = match.group("router")
            method = match.group("method").upper()
            args = match.group("args")
            path_match = STRING_RE.search(args)
            if not path_match:
                continue
            raw_path = normalize_path_params(path_match.group(1))
            prefix = prefixes.get(router_name, "")
            full_path = join_paths(prefix, raw_path)
            if apply_prefix:
                full_path = apply_api_prefix(api_prefix, full_path)

            handler_name = find_next_handler(text, match.end())
            if not handler_name:
                continue

            handler_id = handler_node_id(router_file, handler_name)
            endpoint_id = f"api_endpoint:{method} {full_path}"

            handler_def = func_defs.get(handler_name)
            line = handler_def.lineno if handler_def else None

            graph.add_node(
                handler_id,
                "handler",
                label=handler_name,
                file=router_file.as_posix(),
                line=line,
                symbol=handler_name,
            )
            graph.add_node(
                endpoint_id,
                "api_endpoint",
                label=f"{method} {full_path}",
                method=method,
                path=full_path,
                file=router_file.as_posix(),
            )
            graph.add_edge(endpoint_id, handler_id, "handled_by")

            if handler_def:
                for node in ast.walk(handler_def):
                    if isinstance(node, ast.Call):
                        target_name = None
                        if isinstance(node.func, ast.Name):
                            target_name = node.func.id
                        elif isinstance(node.func, ast.Attribute) and isinstance(
                            node.func.value, ast.Name
                        ):
                            target_name = node.func.value.id
                        if target_name and target_name in service_imports:
                            module = service_imports[target_name]
                            graph.add_node(
                                service_node_id(module, target_name),
                                "service",
                                label=target_name,
                                file=(module_to_path(module) or router_file).as_posix(),
                            )
                            graph.add_edge(handler_id, service_node_id(module, target_name), "handler_calls_service")

                annotations = set()
                annotations.update(extract_annotation_names(handler_def.returns))
                for arg in handler_def.args.args + handler_def.args.kwonlyargs:
                    annotations.update(extract_annotation_names(arg.annotation))
                for name in annotations:
                    if name in schema_imports:
                        module = schema_imports[name]
                        graph.add_node(
                            schema_node_id(module, name),
                            "schema",
                            label=name,
                            file=(module_to_path(module) or router_file).as_posix(),
                        )
                        graph.add_edge(handler_id, schema_node_id(module, name), "handler_uses_schema")

    server_file = api_root / "server.py"
    if server_file.exists():
        text = server_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = ast.parse("")

        func_defs: Dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_defs[node.name] = node

        for match in APP_DECORATOR_RE.finditer(text):
            method = match.group("method").upper()
            args = match.group("args")
            path_match = STRING_RE.search(args)
            if not path_match:
                continue
            raw_path = normalize_path_params(path_match.group(1))
            full_path = resolve_app_path(raw_path, api_prefix or "")
            handler_name = find_next_handler(text, match.end())
            if not handler_name:
                continue

            handler_id = handler_node_id(server_file, handler_name)
            endpoint_id = f"api_endpoint:{method} {full_path}"
            handler_def = func_defs.get(handler_name)
            line = handler_def.lineno if handler_def else None

            graph.add_node(
                handler_id,
                "handler",
                label=handler_name,
                file=server_file.as_posix(),
                line=line,
                symbol=handler_name,
            )
            graph.add_node(
                endpoint_id,
                "api_endpoint",
                label=f"{method} {full_path}",
                method=method,
                path=full_path,
                file=server_file.as_posix(),
            )
            graph.add_edge(endpoint_id, handler_id, "handled_by")

    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract backend handlers and service usage.")
    parser.add_argument(
        "--api-root",
        default="skillmeat/api",
        help="Path to API root (default: skillmeat/api)",
    )
    parser.add_argument(
        "--out",
        default="docs/architecture/codebase-graph.backend.handlers.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    graph = extract_backend_handlers(Path(args.api_root))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    graph.write_json(args.out)


if __name__ == "__main__":
    main()
