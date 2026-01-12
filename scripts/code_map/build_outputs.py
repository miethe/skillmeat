from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _load_graph(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _node_index(nodes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {node["id"]: node for node in nodes}


def _display_name(node: Dict[str, Any]) -> str:
    label = node.get("label")
    if label:
        return str(label)
    node_id = node.get("id", "")
    if "::" in node_id:
        return node_id.split("::")[-1]
    return node_id


def _update_section(path: Path, start: str, end: str, content: str) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    text = path.read_text(encoding="utf-8")
    if start not in text or end not in text:
        raise ValueError(f"Missing markers in {path}")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    updated = before + start + "\n" + content.rstrip() + "\n" + end + after
    path.write_text(updated, encoding="utf-8")


def _format_table(headers: List[str], rows: Iterable[List[str]]) -> str:
    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def _format_list(values: Iterable[str]) -> str:
    values = [value for value in values if value]
    if not values:
        return "-"
    return ", ".join(sorted(set(values)))


def build_hooks_table(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    node_index = _node_index(nodes)
    hook_nodes = [node for node in nodes if node.get("type") == "hook"]

    hook_clients: Dict[str, List[str]] = {}
    hook_queries: Dict[str, List[str]] = {}

    for edge in edges:
        if edge.get("type") == "hook_calls_api_client":
            hook_id = edge.get("from")
            client = node_index.get(edge.get("to"))
            if hook_id and client:
                hook_clients.setdefault(hook_id, []).append(_display_name(client))
        if edge.get("type") == "hook_registers_query_key":
            hook_id = edge.get("from")
            query = node_index.get(edge.get("to"))
            if hook_id and query:
                hook_queries.setdefault(hook_id, []).append(_display_name(query))

    rows: List[List[str]] = []
    for node in sorted(hook_nodes, key=_display_name):
        hook_id = node["id"]
        rows.append(
            [
                _display_name(node),
                node.get("file", "-"),
                _format_list(hook_clients.get(hook_id, [])),
                _format_list(hook_queries.get(hook_id, [])),
            ]
        )
    return _format_table(["Hook", "File", "API Clients", "Query Keys"], rows)


def build_api_clients_table(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    node_index = _node_index(nodes)
    client_nodes = [node for node in nodes if node.get("type") == "api_client"]

    client_endpoints: Dict[str, List[str]] = {}
    for edge in edges:
        if edge.get("type") != "api_client_calls_endpoint":
            continue
        client_id = edge.get("from")
        endpoint = node_index.get(edge.get("to"))
        if client_id and endpoint:
            client_endpoints.setdefault(client_id, []).append(_display_name(endpoint))

    rows: List[List[str]] = []
    for node in sorted(client_nodes, key=_display_name):
        client_id = node["id"]
        rows.append(
            [
                _display_name(node),
                node.get("file", "-"),
                _format_list(client_endpoints.get(client_id, [])),
            ]
        )
    return _format_table(["API Client", "File", "Endpoints"], rows)


def build_schemas_table(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> str:
    node_index = _node_index(nodes)
    schema_nodes = [node for node in nodes if node.get("type") == "schema"]

    schema_handlers: Dict[str, List[str]] = {}
    for edge in edges:
        if edge.get("type") != "handler_uses_schema":
            continue
        schema_id = edge.get("to")
        handler = node_index.get(edge.get("from"))
        if schema_id and handler:
            schema_handlers.setdefault(schema_id, []).append(_display_name(handler))

    rows: List[List[str]] = []
    for node in sorted(schema_nodes, key=_display_name):
        schema_id = node["id"]
        rows.append(
            [
                _display_name(node),
                node.get("file", "-"),
                _format_list(schema_handlers.get(schema_id, [])),
            ]
        )
    return _format_table(["Schema", "File", "Handlers"], rows)


def build_outputs(graph_path: Path) -> None:
    graph = _load_graph(graph_path)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    hooks_table = build_hooks_table(nodes, edges)
    api_clients_table = build_api_clients_table(nodes, edges)
    schemas_table = build_schemas_table(nodes, edges)

    _update_section(
        Path(".claude/rules/web/hooks.md"),
        "<!-- CODEBASE_GRAPH:HOOKS:START -->",
        "<!-- CODEBASE_GRAPH:HOOKS:END -->",
        hooks_table,
    )
    _update_section(
        Path(".claude/rules/web/api-client.md"),
        "<!-- CODEBASE_GRAPH:API_CLIENTS:START -->",
        "<!-- CODEBASE_GRAPH:API_CLIENTS:END -->",
        api_clients_table,
    )
    _update_section(
        Path(".claude/rules/api/schemas.md"),
        "<!-- CODEBASE_GRAPH:SCHEMAS:START -->",
        "<!-- CODEBASE_GRAPH:SCHEMAS:END -->",
        schemas_table,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build rule inventory outputs from the graph.")
    parser.add_argument(
        "--graph",
        default="docs/architecture/codebase-graph.unified.json",
        help="Unified graph JSON path",
    )
    args = parser.parse_args()

    build_outputs(Path(args.graph))


if __name__ == "__main__":
    main()
