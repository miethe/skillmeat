#!/usr/bin/env python3
"""Add comprehensive examples to memory and context module endpoints in openapi.json.

This script adds request and response examples for all memory-items, context-modules,
and context-packs endpoints while preserving existing documentation.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

# Example definitions
EXAMPLES = {
    # Memory Items - CRUD
    "/api/v1/memory-items": {
        "post": {
            "requestBody": {
                "create_decision": {
                    "summary": "Create a decision memory item",
                    "value": {
                        "type": "decision",
                        "content": "Use FastAPI for all new API endpoints to maintain consistency with existing backend architecture.",
                        "confidence": 0.9,
                        "status": "active",
                        "provenance": {
                            "source": "architecture-review",
                            "date": "2025-01-15"
                        },
                        "anchors": ["skillmeat/api/", "fastapi"],
                        "ttl_policy": None
                    }
                },
                "create_gotcha": {
                    "summary": "Create a gotcha memory item",
                    "value": {
                        "type": "gotcha",
                        "content": "Cache refresh must be called after filesystem writes to keep DB in sync.",
                        "confidence": 0.95,
                        "status": "stable",
                        "provenance": {
                            "source": "bug-fix",
                            "issue_id": "BUG-123"
                        },
                        "anchors": ["cache/refresh.py", "write-through pattern"]
                    }
                }
            },
            "responses": {
                "201": {
                    "success": {
                        "summary": "Successfully created memory item",
                        "value": {
                            "id": "mem_abc123",
                            "project_id": "skillmeat",
                            "type": "decision",
                            "content": "Use FastAPI for all new API endpoints to maintain consistency with existing backend architecture.",
                            "confidence": 0.9,
                            "status": "active",
                            "provenance": {
                                "source": "architecture-review",
                                "date": "2025-01-15"
                            },
                            "anchors": ["skillmeat/api/", "fastapi"],
                            "ttl_policy": None,
                            "content_hash": "sha256_abc123",
                            "access_count": 0,
                            "created_at": "2025-02-06T10:30:00Z",
                            "updated_at": "2025-02-06T10:30:00Z",
                            "deprecated_at": None
                        }
                    }
                }
            }
        },
        "get": {
            "responses": {
                "200": {
                    "paginated_list": {
                        "summary": "Paginated list of memory items",
                        "value": {
                            "items": [
                                {
                                    "id": "mem_abc123",
                                    "project_id": "skillmeat",
                                    "type": "decision",
                                    "content": "Use FastAPI for all new API endpoints.",
                                    "confidence": 0.9,
                                    "status": "active",
                                    "access_count": 15,
                                    "created_at": "2025-02-06T10:30:00Z",
                                    "updated_at": "2025-02-06T10:30:00Z"
                                },
                                {
                                    "id": "mem_def456",
                                    "project_id": "skillmeat",
                                    "type": "gotcha",
                                    "content": "Cache refresh must be called after filesystem writes.",
                                    "confidence": 0.95,
                                    "status": "stable",
                                    "access_count": 42,
                                    "created_at": "2025-02-05T14:20:00Z",
                                    "updated_at": "2025-02-06T09:15:00Z"
                                }
                            ],
                            "next_cursor": "mem_ghi789",
                            "has_more": True,
                            "total": 127
                        }
                    }
                }
            }
        }
    },
    "/api/v1/memory-items/{item_id}": {
        "get": {
            "responses": {
                "200": {
                    "single_item": {
                        "summary": "Retrieved memory item",
                        "value": {
                            "id": "mem_abc123",
                            "project_id": "skillmeat",
                            "type": "decision",
                            "content": "Use FastAPI for all new API endpoints to maintain consistency with existing backend architecture.",
                            "confidence": 0.9,
                            "status": "active",
                            "provenance": {
                                "source": "architecture-review",
                                "date": "2025-01-15"
                            },
                            "anchors": ["skillmeat/api/", "fastapi"],
                            "ttl_policy": None,
                            "content_hash": "sha256_abc123",
                            "access_count": 16,
                            "created_at": "2025-02-06T10:30:00Z",
                            "updated_at": "2025-02-06T10:30:00Z",
                            "deprecated_at": None
                        }
                    }
                }
            }
        },
        "put": {
            "requestBody": {
                "update_confidence": {
                    "summary": "Update confidence score",
                    "value": {
                        "confidence": 0.95
                    }
                }
            },
            "responses": {
                "200": {
                    "updated": {
                        "summary": "Successfully updated",
                        "value": {
                            "id": "mem_abc123",
                            "project_id": "skillmeat",
                            "type": "decision",
                            "content": "Use FastAPI for all new API endpoints.",
                            "confidence": 0.95,
                            "status": "active",
                            "access_count": 16,
                            "created_at": "2025-02-06T10:30:00Z",
                            "updated_at": "2025-02-06T11:00:00Z"
                        }
                    }
                }
            }
        }
    },
    # Memory Items - Lifecycle
    "/api/v1/memory-items/{item_id}/promote": {
        "post": {
            "requestBody": {
                "with_reason": {
                    "summary": "Promote with reason",
                    "value": {
                        "reason": "Validated in production for 2 weeks"
                    }
                }
            },
            "responses": {
                "200": {
                    "promoted": {
                        "summary": "Promoted to next stage",
                        "value": {
                            "id": "mem_abc123",
                            "project_id": "skillmeat",
                            "type": "decision",
                            "content": "Use FastAPI for all new API endpoints.",
                            "confidence": 0.9,
                            "status": "stable",
                            "access_count": 20,
                            "created_at": "2025-02-06T10:30:00Z",
                            "updated_at": "2025-02-08T14:00:00Z"
                        }
                    }
                }
            }
        }
    },
    "/api/v1/memory-items/{item_id}/deprecate": {
        "post": {
            "requestBody": {
                "with_reason": {
                    "summary": "Deprecate with reason",
                    "value": {
                        "reason": "Superseded by mem_xyz999"
                    }
                }
            },
            "responses": {
                "200": {
                    "deprecated": {
                        "summary": "Successfully deprecated",
                        "value": {
                            "id": "mem_abc123",
                            "project_id": "skillmeat",
                            "type": "decision",
                            "content": "Use FastAPI for all new API endpoints.",
                            "confidence": 0.9,
                            "status": "deprecated",
                            "access_count": 20,
                            "created_at": "2025-02-06T10:30:00Z",
                            "updated_at": "2025-02-10T09:00:00Z",
                            "deprecated_at": "2025-02-10T09:00:00Z"
                        }
                    }
                }
            }
        }
    },
    "/api/v1/memory-items/bulk-promote": {
        "post": {
            "requestBody": {
                "bulk_promote": {
                    "summary": "Promote multiple items",
                    "value": {
                        "item_ids": ["mem_abc123", "mem_def456", "mem_ghi789"],
                        "reason": "Batch validation after sprint review"
                    }
                }
            },
            "responses": {
                "200": {
                    "partial_success": {
                        "summary": "Bulk operation with partial failures",
                        "value": {
                            "succeeded": ["mem_abc123", "mem_def456"],
                            "failed": [
                                {
                                    "id": "mem_ghi789",
                                    "error": "Item not found"
                                }
                            ]
                        }
                    }
                }
            }
        }
    },
    "/api/v1/memory-items/bulk-deprecate": {
        "post": {
            "requestBody": {
                "bulk_deprecate": {
                    "summary": "Deprecate multiple items",
                    "value": {
                        "item_ids": ["mem_old123", "mem_old456"],
                        "reason": "Cleanup of obsolete memories"
                    }
                }
            },
            "responses": {
                "200": {
                    "all_success": {
                        "summary": "All items deprecated successfully",
                        "value": {
                            "succeeded": ["mem_old123", "mem_old456"],
                            "failed": []
                        }
                    }
                }
            }
        }
    },
    # Memory Items - Merge
    "/api/v1/memory-items/merge": {
        "post": {
            "requestBody": {
                "combine_strategy": {
                    "summary": "Merge with combine strategy",
                    "value": {
                        "source_id": "mem_source123",
                        "target_id": "mem_target456",
                        "strategy": "combine",
                        "merged_content": "Use FastAPI for all new API endpoints. Prefer async handlers for I/O operations."
                    }
                }
            },
            "responses": {
                "200": {
                    "merged": {
                        "summary": "Successfully merged",
                        "value": {
                            "item": {
                                "id": "mem_target456",
                                "project_id": "skillmeat",
                                "type": "decision",
                                "content": "Use FastAPI for all new API endpoints. Prefer async handlers for I/O operations.",
                                "confidence": 0.92,
                                "status": "active",
                                "access_count": 25,
                                "created_at": "2025-02-05T10:30:00Z",
                                "updated_at": "2025-02-10T15:30:00Z"
                            },
                            "merged_source_id": "mem_source123"
                        }
                    }
                }
            }
        }
    },
    "/api/v1/memory-items/count": {
        "get": {
            "responses": {
                "200": {
                    "count": {
                        "summary": "Count of filtered items",
                        "value": {
                            "count": 127
                        }
                    }
                }
            }
        }
    },
    # Context Modules
    "/api/v1/context-modules": {
        "post": {
            "requestBody": {
                "create_module": {
                    "summary": "Create context module with selectors",
                    "value": {
                        "name": "api-development",
                        "description": "Context for API development workflows",
                        "selectors": {
                            "memory_types": ["decision", "gotcha"],
                            "min_confidence": 0.8,
                            "file_patterns": ["skillmeat/api/**"],
                            "workflow_stages": ["development", "review"]
                        },
                        "priority": 10
                    }
                }
            },
            "responses": {
                "201": {
                    "created": {
                        "summary": "Successfully created module",
                        "value": {
                            "id": "ctx_mod_abc123",
                            "project_id": "skillmeat",
                            "name": "api-development",
                            "description": "Context for API development workflows",
                            "selectors": {
                                "memory_types": ["decision", "gotcha"],
                                "min_confidence": 0.8,
                                "file_patterns": ["skillmeat/api/**"],
                                "workflow_stages": ["development", "review"]
                            },
                            "priority": 10,
                            "content_hash": "sha256_xyz789",
                            "created_at": "2025-02-10T10:00:00Z",
                            "updated_at": "2025-02-10T10:00:00Z",
                            "memory_items": None
                        }
                    }
                }
            }
        },
        "get": {
            "responses": {
                "200": {
                    "list": {
                        "summary": "List of context modules",
                        "value": {
                            "items": [
                                {
                                    "id": "ctx_mod_abc123",
                                    "project_id": "skillmeat",
                                    "name": "api-development",
                                    "description": "Context for API development workflows",
                                    "priority": 10,
                                    "created_at": "2025-02-10T10:00:00Z"
                                },
                                {
                                    "id": "ctx_mod_def456",
                                    "project_id": "skillmeat",
                                    "name": "frontend-patterns",
                                    "description": "React/Next.js component patterns",
                                    "priority": 5,
                                    "created_at": "2025-02-09T14:30:00Z"
                                }
                            ],
                            "next_cursor": "ctx_mod_ghi789",
                            "has_more": False,
                            "total": 2
                        }
                    }
                }
            }
        }
    },
    "/api/v1/context-modules/{module_id}": {
        "get": {
            "responses": {
                "200": {
                    "with_items": {
                        "summary": "Module with associated memory items",
                        "value": {
                            "id": "ctx_mod_abc123",
                            "project_id": "skillmeat",
                            "name": "api-development",
                            "description": "Context for API development workflows",
                            "selectors": {
                                "memory_types": ["decision", "gotcha"],
                                "min_confidence": 0.8
                            },
                            "priority": 10,
                            "content_hash": "sha256_xyz789",
                            "created_at": "2025-02-10T10:00:00Z",
                            "updated_at": "2025-02-10T10:00:00Z",
                            "memory_items": [
                                {
                                    "id": "mem_abc123",
                                    "type": "decision",
                                    "content": "Use FastAPI for all new API endpoints.",
                                    "confidence": 0.9
                                }
                            ]
                        }
                    }
                }
            }
        },
        "put": {
            "requestBody": {
                "update_selectors": {
                    "summary": "Update module selectors",
                    "value": {
                        "selectors": {
                            "memory_types": ["decision", "gotcha", "style_rule"],
                            "min_confidence": 0.85
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "updated": {
                        "summary": "Successfully updated",
                        "value": {
                            "id": "ctx_mod_abc123",
                            "project_id": "skillmeat",
                            "name": "api-development",
                            "selectors": {
                                "memory_types": ["decision", "gotcha", "style_rule"],
                                "min_confidence": 0.85
                            },
                            "priority": 10,
                            "updated_at": "2025-02-10T11:00:00Z"
                        }
                    }
                }
            }
        }
    },
    "/api/v1/context-modules/{module_id}/memories": {
        "post": {
            "requestBody": {
                "add_memory": {
                    "summary": "Add memory to module",
                    "value": {
                        "memory_id": "mem_abc123",
                        "ordering": 5
                    }
                }
            },
            "responses": {
                "200": {
                    "added": {
                        "summary": "Memory added to module",
                        "value": {
                            "id": "ctx_mod_abc123",
                            "project_id": "skillmeat",
                            "name": "api-development",
                            "memory_items": [
                                {
                                    "id": "mem_abc123",
                                    "type": "decision",
                                    "content": "Use FastAPI for all new API endpoints.",
                                    "ordering": 5
                                }
                            ]
                        }
                    }
                }
            }
        },
        "get": {
            "responses": {
                "200": {
                    "memories_list": {
                        "summary": "List of module's memories",
                        "value": [
                            {
                                "id": "mem_abc123",
                                "type": "decision",
                                "content": "Use FastAPI for all new API endpoints.",
                                "confidence": 0.9,
                                "ordering": 5
                            },
                            {
                                "id": "mem_def456",
                                "type": "gotcha",
                                "content": "Cache refresh must be called after filesystem writes.",
                                "confidence": 0.95,
                                "ordering": 10
                            }
                        ]
                    }
                }
            }
        }
    },
    # Context Packing
    "/api/v1/context-packs/preview": {
        "post": {
            "requestBody": {
                "with_budget": {
                    "summary": "Preview pack with token budget",
                    "value": {
                        "module_id": "ctx_mod_abc123",
                        "budget_tokens": 4000,
                        "filters": {
                            "type": "decision",
                            "min_confidence": 0.85
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "preview": {
                        "summary": "Pack preview with statistics",
                        "value": {
                            "items": [
                                {
                                    "id": "mem_abc123",
                                    "type": "decision",
                                    "content": "Use FastAPI for all new API endpoints.",
                                    "confidence": 0.9,
                                    "tokens": 15
                                },
                                {
                                    "id": "mem_def456",
                                    "type": "decision",
                                    "content": "Prefer async handlers for I/O operations.",
                                    "confidence": 0.88,
                                    "tokens": 12
                                }
                            ],
                            "total_tokens": 27,
                            "budget_tokens": 4000,
                            "utilization": 0.00675,
                            "items_included": 2,
                            "items_available": 2
                        }
                    }
                }
            }
        }
    },
    "/api/v1/context-packs/generate": {
        "post": {
            "requestBody": {
                "generate_pack": {
                    "summary": "Generate full context pack",
                    "value": {
                        "module_id": "ctx_mod_abc123",
                        "budget_tokens": 4000,
                        "filters": {
                            "min_confidence": 0.8
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "generated": {
                        "summary": "Generated context pack with markdown",
                        "value": {
                            "items": [
                                {
                                    "id": "mem_abc123",
                                    "type": "decision",
                                    "content": "Use FastAPI for all new API endpoints.",
                                    "confidence": 0.9,
                                    "tokens": 15
                                }
                            ],
                            "total_tokens": 15,
                            "budget_tokens": 4000,
                            "utilization": 0.00375,
                            "items_included": 1,
                            "items_available": 1,
                            "markdown": "# Context Pack\\n\\n## Decisions\\n\\n- Use FastAPI for all new API endpoints.\\n\\n---\\nGenerated at: 2025-02-10T15:30:00Z",
                            "generated_at": "2025-02-10T15:30:00Z"
                        }
                    }
                }
            }
        }
    }
}


def add_examples_to_endpoint(openapi: Dict[str, Any], path: str, method: str, examples: Dict[str, Any]) -> None:
    """Add examples to a specific endpoint in the OpenAPI spec.

    Args:
        openapi: The OpenAPI specification dict
        path: API path (e.g., "/api/v1/memory-items")
        method: HTTP method (e.g., "post", "get")
        examples: Dict with "requestBody" and/or "responses" keys containing examples
    """
    if path not in openapi["paths"]:
        print(f"Warning: Path {path} not found in openapi.json")
        return

    if method not in openapi["paths"][path]:
        print(f"Warning: Method {method} not found for {path}")
        return

    endpoint = openapi["paths"][path][method]

    # Add request body examples
    if "requestBody" in examples and "requestBody" in endpoint:
        request_examples = examples["requestBody"]
        content = endpoint["requestBody"].get("content", {})
        app_json = content.get("application/json", {})

        if app_json:
            if "examples" not in app_json:
                app_json["examples"] = {}
            app_json["examples"].update(request_examples)
            print(f"  Added {len(request_examples)} request example(s) to {method.upper()} {path}")

    # Add response examples
    if "responses" in examples and "responses" in endpoint:
        for status_code, response_examples in examples["responses"].items():
            if status_code in endpoint["responses"]:
                response = endpoint["responses"][status_code]
                content = response.get("content", {})
                app_json = content.get("application/json", {})

                if app_json:
                    if "examples" not in app_json:
                        app_json["examples"] = {}
                    app_json["examples"].update(response_examples)
                    print(f"  Added {len(response_examples)} response example(s) to {method.upper()} {path} [{status_code}]")


def main():
    """Add examples to all memory and context module endpoints in openapi.json."""
    openapi_path = Path(__file__).parent.parent.parent / "skillmeat" / "api" / "openapi.json"

    if not openapi_path.exists():
        print(f"Error: {openapi_path} not found")
        sys.exit(1)

    print(f"Reading {openapi_path}")
    with open(openapi_path, "r", encoding="utf-8") as f:
        openapi = json.load(f)

    print("\nAdding examples to memory and context module endpoints...")

    # Process all endpoints
    for path, methods in EXAMPLES.items():
        for method, examples in methods.items():
            add_examples_to_endpoint(openapi, path, method, examples)

    print(f"\nWriting updated openapi.json...")
    with open(openapi_path, "w", encoding="utf-8") as f:
        json.dump(openapi, f, indent=2, ensure_ascii=False)

    print("✓ Successfully added examples to openapi.json")


if __name__ == "__main__":
    main()
