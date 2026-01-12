from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Graph:
    source: str
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: List[Dict[str, Any]] = field(default_factory=list)

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: Optional[str] = None,
        file: Optional[str] = None,
        **extra: Any,
    ) -> None:
        if node_id in self.nodes:
            existing = self.nodes[node_id]
            existing.update({k: v for k, v in extra.items() if v is not None})
            if label and not existing.get("label"):
                existing["label"] = label
            if file and not existing.get("file"):
                existing["file"] = file
            return
        node = {"id": node_id, "type": node_type}
        if label:
            node["label"] = label
        if file:
            node["file"] = file
        for key, value in extra.items():
            if value is not None:
                node[key] = value
        self.nodes[node_id] = node

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: str,
        **extra: Any,
    ) -> None:
        edge = {"from": from_id, "to": to_id, "type": edge_type}
        for key, value in extra.items():
            if value is not None:
                edge[key] = value
        self.edges.append(edge)

    def merge(self, other: "Graph") -> None:
        for node_id, node in other.nodes.items():
            if node_id not in self.nodes:
                self.nodes[node_id] = node
        self.edges.extend(other.edges)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "nodes": list(self.nodes.values()),
            "edges": self.edges,
        }

    def write_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2, sort_keys=True)
            handle.write("\n")
