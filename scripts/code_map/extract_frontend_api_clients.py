from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

try:
    from .graph import Graph
    from .frontend_utils import parse_imports, resolve_module_path
except ImportError:  # pragma: no cover - fallback for direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.code_map.graph import Graph
    from scripts.code_map.frontend_utils import parse_imports, resolve_module_path

EXPORT_FUNC_RE = re.compile(r"export\s+(?:async\s+)?function\s+([A-Za-z0-9_]+)\s*\(")
EXPORT_CONST_RE = re.compile(r"export\s+const\s+([A-Za-z0-9_]+)\s*=\s*(?:async\s*)?\(")
API_REQUEST_RE = re.compile(r"apiRequest(?:<[^>]*>)?\(\s*([`'\"])(.+?)\1", re.DOTALL)
FETCH_RE = re.compile(r"fetch\(\s*([`'\"])(/.+?)\1", re.DOTALL)
BUILD_URL_RE = re.compile(r"build(?:Url|ApiUrl)\(\s*([`'\"])(.+?)\1", re.DOTALL)
METHOD_RE = re.compile(r"method\s*:\s*['\"]([A-Z]+)['\"]")
HOOK_EXPORT_FUNC_RE = re.compile(r"export\s+function\s+(use[A-Za-z0-9_]+)\b")
HOOK_EXPORT_CONST_RE = re.compile(r"export\s+const\s+(use[A-Za-z0-9_]+)\b")


def iter_api_files(web_root: Path) -> List[Path]:
    files: List[Path] = []
    api_root = web_root / "lib" / "api"
    if api_root.exists():
        files.extend(api_root.rglob("*.ts"))
    api_file = web_root / "lib" / "api.ts"
    if api_file.exists():
        files.append(api_file)
    return files


def extract_exported_functions(text: str) -> List[Tuple[str, int]]:
    matches: List[Tuple[str, int]] = []
    for match in EXPORT_FUNC_RE.finditer(text):
        matches.append((match.group(1), match.start()))
    for match in EXPORT_CONST_RE.finditer(text):
        matches.append((match.group(1), match.start()))
    return sorted(matches, key=lambda item: item[1])


def slice_functions(text: str, functions: List[Tuple[str, int]]) -> Dict[str, str]:
    sliced: Dict[str, str] = {}
    for index, (name, start) in enumerate(functions):
        end = functions[index + 1][1] if index + 1 < len(functions) else len(text)
        sliced[name] = text[start:end]
    return sliced


def find_endpoints(text: str) -> List[Tuple[str, Optional[str]]]:
    endpoints: List[Tuple[str, Optional[str]]] = []
    for match in API_REQUEST_RE.finditer(text):
        path = match.group(2)
        window = text[match.end() : match.end() + 300]
        method_match = METHOD_RE.search(window)
        method = method_match.group(1) if method_match else None
        endpoints.append((path, method))
    for match in BUILD_URL_RE.finditer(text):
        path = match.group(2)
        window = text[match.end() : match.end() + 300]
        method_match = METHOD_RE.search(window)
        method = method_match.group(1) if method_match else None
        endpoints.append((path, method))
    for match in FETCH_RE.finditer(text):
        path = match.group(2)
        endpoints.append((path, None))
    return endpoints


def api_client_node_id(path: Path, name: str) -> str:
    return f"api_client:{path.as_posix()}::{name}"


def hook_node_ids(path: Path, names: Sequence[str]) -> List[str]:
    return [f"hook:{path.as_posix()}::{name}" for name in names]


def extract_frontend_api_clients(web_root: Path) -> Graph:
    graph = Graph(source="frontend")
    api_files = iter_api_files(web_root)

    exported_functions: Dict[Path, List[str]] = {}
    export_to_file: Dict[str, Path] = {}

    for api_file in api_files:
        text = api_file.read_text(encoding="utf-8")
        export_matches = extract_exported_functions(text)
        functions = [name for name, _ in export_matches]
        if not functions:
            continue
        exported_functions[api_file] = functions
        for name in functions:
            export_to_file.setdefault(name, api_file)
            graph.add_node(
                api_client_node_id(api_file, name),
                "api_client",
                label=name,
                file=api_file.as_posix(),
            )
        function_slices = slice_functions(text, export_matches)
        for name, body in function_slices.items():
            for path, method in find_endpoints(body):
                endpoint_label = f"{method} {path}" if method else path
                endpoint_id = f"endpoint:{endpoint_label}"
                graph.add_node(
                    endpoint_id,
                    "api_endpoint",
                    label=endpoint_label,
                    method=method,
                    path=path,
                    file=api_file.as_posix(),
                )
                graph.add_edge(
                    api_client_node_id(api_file, name),
                    endpoint_id,
                    "api_client_calls_endpoint",
                )

    hooks_root = web_root / "hooks"
    if hooks_root.exists():
        for hook_path in hooks_root.rglob("*.ts*"):
            text = hook_path.read_text(encoding="utf-8")
            imports = parse_imports(text)
            hook_exports = set(HOOK_EXPORT_FUNC_RE.findall(text))
            hook_exports.update(HOOK_EXPORT_CONST_RE.findall(text))
            hook_names = sorted(hook_exports)
            if not hook_names:
                continue
            for names, module in imports:
                if not module.startswith("@/lib/api") and not module.startswith("."):
                    continue
                resolved = resolve_module_path(web_root, hook_path, module)
                for name in names:
                    target_path = resolved
                    if not target_path and module.startswith("@/lib/api"):
                        target_path = export_to_file.get(name)
                    if not target_path:
                        continue
                    client_id = api_client_node_id(target_path, name)
                    graph.add_node(
                        client_id,
                        "api_client",
                        label=name,
                        file=target_path.as_posix(),
                    )
                    for hook_id in hook_node_ids(hook_path, hook_names):
                        graph.add_node(
                            hook_id,
                            "hook",
                            label=hook_id.split("::")[-1],
                            file=hook_path.as_posix(),
                        )
                        graph.add_edge(hook_id, client_id, "hook_calls_api_client")

    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract frontend API client graph.")
    parser.add_argument(
        "--web-root",
        default="skillmeat/web",
        help="Path to web root (default: skillmeat/web)",
    )
    parser.add_argument(
        "--out",
        default="docs/architecture/codebase-graph.frontend.api-clients.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    graph = extract_frontend_api_clients(Path(args.web_root))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    graph.write_json(args.out)


if __name__ == "__main__":
    main()
