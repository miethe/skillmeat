from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


def _load_graph(path: Path) -> Dict[str, Any]:
    if not path.exists():
        print(f"ERROR: graph file not found: {path}")
        print("Build the unified graph first:")
        print("- python -m scripts.code_map.merge_graphs")
        print("- python -m scripts.code_map.apply_overrides")
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _count_by_key(items: List[Dict[str, Any]], key: str) -> Counter:
    counter: Counter = Counter()
    for item in items:
        value = item.get(key, "<missing>")
        counter[value] += 1
    return counter


def _print_counter(title: str, counter: Counter) -> None:
    print(title)
    for item, count in counter.most_common():
        print(f"- {item}: {count}")
    print()


def _hooks_missing_calls_api(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[str]:
    hook_ids = {node["id"] for node in nodes if node.get("type") == "hook"}
    calls_api = {edge["from"] for edge in edges if edge.get("type") == "calls_api"}
    return sorted(hook_ids - calls_api)


def coverage_summary(graph: Dict[str, Any], max_list: int) -> None:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    _print_counter("Node counts by type:", _count_by_key(nodes, "type"))
    _print_counter("Edge counts by type:", _count_by_key(edges, "type"))

    missing_hooks = _hooks_missing_calls_api(nodes, edges)
    print("Missing links:")
    print(f"- hooks_missing_calls_api: {len(missing_hooks)}")
    if missing_hooks and max_list > 0:
        print("- sample:")
        for hook_id in missing_hooks[:max_list]:
            print(f"  - {hook_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize graph coverage.")
    parser.add_argument(
        "--graph",
        default="docs/architecture/codebase-graph.unified.json",
        help="Unified graph JSON path",
    )
    parser.add_argument(
        "--max-list",
        type=int,
        default=20,
        help="Max number of missing items to list",
    )
    args = parser.parse_args()

    try:
        graph = _load_graph(Path(args.graph))
    except FileNotFoundError:
        sys.exit(1)
    coverage_summary(graph, args.max_list)


if __name__ == "__main__":
    main()
