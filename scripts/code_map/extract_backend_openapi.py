from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable

try:
    from .graph import Graph
except ImportError:  # pragma: no cover - fallback for direct script execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.code_map.graph import Graph


def _load_openapi(path: Path) -> Dict[str, Any]:
    if not path.exists():
        try:
            from skillmeat.api.openapi import export_openapi_spec
            from skillmeat.api.server import create_app
        except Exception as exc:
            raise FileNotFoundError(path) from exc
        app = create_app()
        export_openapi_spec(app, output_path=path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _iter_operations(spec: Dict[str, Any]) -> Iterable[tuple[str, str, Dict[str, Any]]]:
    for raw_path, methods in (spec.get("paths") or {}).items():
        for method, operation in methods.items():
            if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            yield raw_path, method.upper(), operation


def extract_backend_openapi(openapi_path: Path) -> Graph:
    graph = Graph(source="backend")
    spec = _load_openapi(openapi_path)

    for raw_path, method, operation in _iter_operations(spec):
        label = f"{method} {raw_path}"
        node_id = f"api_endpoint:{label}"
        graph.add_node(
            node_id,
            "api_endpoint",
            label=label,
            method=method,
            path=raw_path,
            operation_id=operation.get("operationId"),
            summary=operation.get("summary"),
            file=openapi_path.as_posix(),
        )
    return graph


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract backend endpoints from OpenAPI spec.")
    parser.add_argument(
        "--openapi",
        default="skillmeat/api/openapi.json",
        help="Path to OpenAPI JSON (default: skillmeat/api/openapi.json)",
    )
    parser.add_argument(
        "--out",
        default="docs/architecture/codebase-graph.backend.openapi.json",
        help="Output JSON path",
    )
    args = parser.parse_args()

    graph = extract_backend_openapi(Path(args.openapi))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    graph.write_json(args.out)


if __name__ == "__main__":
    main()
