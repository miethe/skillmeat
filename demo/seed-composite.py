#!/usr/bin/env python3
"""Seed the fin-serv-compliance composite with demo context artifacts.

Reads content files from demo/seed-artifacts/fin-serv-compliance/ and populates
the SkillMeat database via API calls:

  1. Create each context entity  →  POST /api/v1/context-entities
  2. Create the composite        →  POST /api/v1/composites
  3. Add each entity as member   →  POST /api/v1/composites/{composite_id}/members

Usage:
    python demo/seed-composite.py [--api-url http://localhost:8080] [--dry-run] [--verbose]
    python demo/seed-composite.py --clean      # delete and recreate everything
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import httpx

# ---------------------------------------------------------------------------
# ANSI color helpers (no external deps)
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"


def _c(color: str, text: str) -> str:
    """Wrap text in ANSI color codes (only when stdout is a TTY)."""
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


def ok(msg: str) -> str:
    return _c(GREEN, f"  [+] {msg}")


def skip(msg: str) -> str:
    return _c(YELLOW, f"  [-] {msg}")


def err(msg: str) -> str:
    return _c(RED, f"  [!] {msg}")


def info(msg: str) -> str:
    return _c(CYAN, f"  ... {msg}")


def header(msg: str) -> str:
    return _c(BOLD, f"\n{msg}")


# ---------------------------------------------------------------------------
# Seed definitions
# ---------------------------------------------------------------------------

# Base directory for seed content files (relative to this script's location)
SEED_BASE = Path(__file__).parent / "seed-artifacts" / "fin-serv-compliance"

# Ordered list of context entity definitions.
# 'file' is relative to SEED_BASE.
ARTIFACTS: list[dict] = [
    {
        "file": "CLAUDE.md",
        "name": "fin-serv-project-config",
        "entity_type": "project_config",
        "path_pattern": ".claude/CLAUDE.md",
        "description": "Project configuration and compliance framework for financial services systems",
        "category": "compliance",
        "auto_load": False,
        "position": 0,
    },
    {
        "file": "context/api-security-standards.md",
        "name": "fin-serv-api-security-standards",
        "entity_type": "context_file",
        "path_pattern": ".claude/context/api-security-standards.md",
        "description": "PCI-DSS compliant API security patterns and authentication standards",
        "category": "security",
        "auto_load": False,
        "position": 1,
    },
    {
        "file": "context/data-handling-policy.md",
        "name": "fin-serv-data-handling-policy",
        "entity_type": "context_file",
        "path_pattern": ".claude/context/data-handling-policy.md",
        "description": "PII classification, encryption requirements, and data retention policies",
        "category": "compliance",
        "auto_load": False,
        "position": 2,
    },
    {
        "file": "context/regulatory-compliance.md",
        "name": "fin-serv-regulatory-compliance",
        "entity_type": "context_file",
        "path_pattern": ".claude/context/regulatory-compliance.md",
        "description": "SOX, AML/KYC, BSA, GDPR, and GLBA regulatory framework reference",
        "category": "compliance",
        "auto_load": False,
        "position": 3,
    },
    {
        "file": "rules/security.md",
        "name": "fin-serv-security-rules",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/security.md",
        "description": "Security coding rules: authentication, secrets management, audit logging",
        "category": "security",
        "auto_load": False,
        "position": 4,
    },
    {
        "file": "rules/data-privacy.md",
        "name": "fin-serv-data-privacy-rules",
        "entity_type": "rule_file",
        "path_pattern": ".claude/rules/data-privacy.md",
        "description": "PII handling invariants and data privacy enforcement rules",
        "category": "privacy",
        "auto_load": False,
        "position": 5,
    },
    {
        "file": "specs/pre-deploy-compliance-checklist.md",
        "name": "fin-serv-pre-deploy-compliance-checklist",
        "entity_type": "spec_file",
        "path_pattern": ".claude/specs/pre-deploy-compliance-checklist.md",
        "description": "Required sign-offs and checks before any production deployment",
        "category": "compliance",
        "auto_load": False,
        "position": 6,
    },
]

COMPOSITE: dict = {
    "composite_id": "composite:fin-serv-compliance",
    "collection_id": "default",
    "composite_type": "suite",
    "display_name": "Financial Services Compliance Pack",
    "description": (
        "Golden context pack for new financial services projects. "
        "Includes API security standards, data handling policies, regulatory compliance "
        "guides, security rules, data privacy rules, and a pre-deployment compliance "
        "checklist. Designed for PCI-DSS, SOX, AML/KYC, GDPR, and GLBA compliance."
    ),
}


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


class APIError(Exception):
    """Raised when an API call returns an unexpected status code."""

    def __init__(self, method: str, url: str, status: int, body: str) -> None:
        self.method = method
        self.url = url
        self.status = status
        self.body = body
        super().__init__(f"{method} {url} → HTTP {status}: {body[:200]}")



def _api(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    json_body: Optional[dict] = None,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[Optional[dict], int]:
    """Wrapper around _request that always returns (data, status_code)."""
    if dry_run:
        print(info(f"[DRY RUN] {method} {url}"))
        if json_body and verbose:
            print(_c(DIM, f"    body: {json.dumps(json_body, indent=2)[:400]}"))
        return None, 0

    if verbose:
        print(info(f"{method} {url}"))
        if json_body:
            print(_c(DIM, f"    → {json.dumps(json_body)[:300]}"))

    response = client.request(method, url, json=json_body)

    if verbose:
        print(_c(DIM, f"    ← HTTP {response.status_code}"))

    if response.status_code == 204:
        return None, 204

    try:
        data = response.json()
    except Exception:
        data = {"_raw": response.text}

    return data, response.status_code


def _is_already_exists_error(status: int, data: Optional[dict]) -> bool:
    """Return True if the response indicates a duplicate/conflict."""
    if status in (409, 400):
        if data is None:
            return False
        detail = str(data.get("detail", "")).lower()
        return any(
            phrase in detail
            for phrase in ("already exists", "already a member", "conflict", "duplicate", "unique")
        )
    return False


# ---------------------------------------------------------------------------
# Core operations
# ---------------------------------------------------------------------------


def read_content(artifact_def: dict) -> str:
    """Read the content of a seed file.

    The file content is returned as-is (including any frontmatter), since
    Claude Code context entities are expected to carry their frontmatter.

    Args:
        artifact_def: Artifact definition dict from ARTIFACTS list.

    Returns:
        Full file content as a string.

    Raises:
        SystemExit: If the file does not exist.
    """
    path = SEED_BASE / artifact_def["file"]
    if not path.exists():
        print(err(f"Seed file not found: {path}"))
        sys.exit(1)
    return path.read_text(encoding="utf-8")


def create_entity(
    client: httpx.Client,
    artifact_def: dict,
    api_base: str,
    dry_run: bool,
    verbose: bool,
) -> tuple[Optional[str], str]:
    """Create a context entity via the API.

    Args:
        client: httpx.Client instance.
        artifact_def: Artifact definition from ARTIFACTS.
        api_base: Base URL of the SkillMeat API.
        dry_run: Skip actual HTTP calls when True.
        verbose: Print request/response details when True.

    Returns:
        Tuple of (entity_id_or_None, status) where status is one of:
        "created", "skipped", "error".
    """
    if not dry_run:
        # Check for existing entity with the same name first (API allows
        # duplicate names, so we need to handle idempotency ourselves).
        existing_id = _fetch_entity_id_by_name(
            client, artifact_def["name"], api_base, verbose
        )
        if existing_id is not None:
            return existing_id, "skipped"

    content = read_content(artifact_def)
    payload = {
        "name": artifact_def["name"],
        "entity_type": artifact_def["entity_type"],
        "content": content,
        "path_pattern": artifact_def["path_pattern"],
        "description": artifact_def["description"],
        "category": artifact_def["category"],
        "auto_load": artifact_def.get("auto_load", False),
    }

    data, status = _api(
        client,
        "POST",
        f"{api_base}/api/v1/context-entities",
        json_body=payload,
        dry_run=dry_run,
        verbose=verbose,
    )

    if dry_run:
        return None, "dry_run"

    if status == 201:
        entity_id = data.get("id") if data else None
        return entity_id, "created"

    if _is_already_exists_error(status, data):
        entity_id = _fetch_entity_id_by_name(
            client, artifact_def["name"], api_base, verbose
        )
        return entity_id, "skipped"

    # Unexpected error
    detail = data.get("detail", data) if data else f"HTTP {status}"
    print(err(f"Failed to create entity '{artifact_def['name']}': {detail}"))
    return None, "error"


def _fetch_entity_id_by_name(
    client: httpx.Client, name: str, api_base: str, verbose: bool
) -> Optional[str]:
    """Look up an existing entity ID by name via list endpoint.

    Args:
        client: httpx.Client instance.
        name: Entity name to search for.
        api_base: Base API URL.
        verbose: Print request details when True.

    Returns:
        Entity ID string, or None if not found.
    """
    data, status = _api(
        client,
        "GET",
        f"{api_base}/api/v1/context-entities?search={name}&page_size=50",
        verbose=verbose,
    )
    if status == 200 and data:
        items = data.get("items", [])
        for item in items:
            if item.get("name") == name:
                return item.get("id")
    return None


def create_composite(
    client: httpx.Client,
    api_base: str,
    dry_run: bool,
    verbose: bool,
) -> tuple[bool, str]:
    """Create the fin-serv-compliance composite artifact.

    Args:
        client: httpx.Client instance.
        api_base: Base API URL.
        dry_run: Skip actual HTTP calls when True.
        verbose: Print request/response details when True.

    Returns:
        Tuple of (success, status) where status is "created", "skipped", or "error".
    """
    data, status = _api(
        client,
        "POST",
        f"{api_base}/api/v1/composites",
        json_body=COMPOSITE,
        dry_run=dry_run,
        verbose=verbose,
    )

    if dry_run:
        return True, "dry_run"

    if status == 201:
        return True, "created"

    if _is_already_exists_error(status, data):
        return True, "skipped"

    detail = data.get("detail", data) if data else f"HTTP {status}"
    print(err(f"Failed to create composite: {detail}"))
    return False, "error"


def add_member(
    client: httpx.Client,
    composite_id: str,
    entity_id: str,
    position: int,
    api_base: str,
    dry_run: bool,
    verbose: bool,
) -> str:
    """Add a context entity as a member of the composite.

    Args:
        client: httpx.Client instance.
        composite_id: The composite's type:name ID.
        entity_id: The artifact's DB ID (e.g. "ctx_abc123"). Context entities
            use this format, not type:name.
        position: Display order (0-based).
        api_base: Base API URL.
        dry_run: Skip actual HTTP calls when True.
        verbose: Print request/response details when True.

    Returns:
        One of "added", "skipped", "error", "dry_run".
    """
    # URL-encode the composite_id since it contains ':'
    import urllib.parse

    encoded_id = urllib.parse.quote(composite_id, safe="")
    url = f"{api_base}/api/v1/composites/{encoded_id}/members?collection_id=default"

    payload = {
        "artifact_id": entity_id,
        "relationship_type": "contains",
        "position": position,
    }

    data, status = _api(
        client, "POST", url, json_body=payload, dry_run=dry_run, verbose=verbose
    )

    if dry_run:
        return "dry_run"

    if status == 201:
        return "added"

    if _is_already_exists_error(status, data):
        return "skipped"

    detail = data.get("detail", data) if data else f"HTTP {status}"
    print(err(f"Failed to add member {entity_id} at position {position}: {detail}"))
    return "error"


# ---------------------------------------------------------------------------
# Clean (delete and recreate)
# ---------------------------------------------------------------------------


def clean_existing(
    client: httpx.Client, api_base: str, verbose: bool
) -> None:
    """Delete the composite and all seeded context entities, if they exist.

    Args:
        client: httpx.Client instance.
        api_base: Base API URL.
        verbose: Print request/response details when True.
    """
    import urllib.parse

    print(header("Cleaning existing seed data..."))

    # Delete composite (cascades membership edges)
    composite_id = COMPOSITE["composite_id"]
    encoded_id = urllib.parse.quote(composite_id, safe="")
    _, status = _api(
        client,
        "DELETE",
        f"{api_base}/api/v1/composites/{encoded_id}",
        verbose=verbose,
    )
    if status in (204, 200):
        print(ok(f"Deleted composite '{composite_id}'"))
    elif status == 404:
        print(skip(f"Composite '{composite_id}' not found — nothing to delete"))
    else:
        print(skip(f"Composite delete returned HTTP {status} — continuing"))

    # Delete each context entity
    for artifact_def in ARTIFACTS:
        name = artifact_def["name"]
        entity_id = _fetch_entity_id_by_name(client, name, api_base, verbose)
        if entity_id is None:
            print(skip(f"Entity '{name}' not found — nothing to delete"))
            continue
        _, status = _api(
            client,
            "DELETE",
            f"{api_base}/api/v1/context-entities/{entity_id}",
            verbose=verbose,
        )
        if status in (204, 200):
            print(ok(f"Deleted entity '{name}' ({entity_id})"))
        else:
            print(skip(f"Entity '{name}' delete returned HTTP {status}"))


# ---------------------------------------------------------------------------
# Main seeding flow
# ---------------------------------------------------------------------------


def seed(
    api_base: str,
    dry_run: bool,
    verbose: bool,
    clean: bool,
) -> int:
    """Run the full seeding process.

    Args:
        api_base: Base URL of the SkillMeat API (e.g. "http://localhost:8080").
        dry_run: Print actions without making HTTP calls.
        verbose: Print detailed request/response output.
        clean: Delete and recreate all data before seeding.

    Returns:
        Exit code (0 = success, 1 = partial failure).
    """
    summary = {
        "entities_created": 0,
        "entities_skipped": 0,
        "entities_failed": 0,
        "composite_created": False,
        "composite_skipped": False,
        "members_added": 0,
        "members_skipped": 0,
        "members_failed": 0,
    }

    with httpx.Client(timeout=30.0) as client:
        # Optional clean step
        if clean and not dry_run:
            clean_existing(client, api_base, verbose)

        # ---- Step 1: Create context entities --------------------------------
        print(header("Step 1: Creating context entities..."))

        # Stores mapping from artifact name → entity_id for membership creation
        entity_ids: dict[str, Optional[str]] = {}

        for artifact_def in ARTIFACTS:
            name = artifact_def["name"]
            entity_id, status = create_entity(
                client, artifact_def, api_base, dry_run, verbose
            )

            if status == "created":
                print(ok(f"Created entity '{name}' (id={entity_id})"))
                summary["entities_created"] += 1
            elif status == "skipped":
                print(skip(f"Entity '{name}' already exists (id={entity_id}) — skipping"))
                summary["entities_skipped"] += 1
            elif status == "dry_run":
                print(info(f"[DRY RUN] Would create entity '{name}'"))
            elif status == "error":
                summary["entities_failed"] += 1
                entity_id = None  # will skip membership for this one

            entity_ids[name] = entity_id

        # ---- Step 2: Create composite ---------------------------------------
        print(header("Step 2: Creating composite artifact..."))

        _, composite_status = create_composite(
            client, api_base, dry_run, verbose
        )
        composite_id = COMPOSITE["composite_id"]

        if composite_status == "created":
            print(ok(f"Created composite '{composite_id}'"))
            summary["composite_created"] = True
        elif composite_status == "skipped":
            print(skip(f"Composite '{composite_id}' already exists — skipping creation"))
            summary["composite_skipped"] = True
        elif composite_status == "dry_run":
            print(info(f"[DRY RUN] Would create composite '{composite_id}'"))
        elif composite_status == "error":
            print(err("Composite creation failed. Aborting membership step."))
            _print_summary(summary)
            return 1

        # ---- Step 3: Add members --------------------------------------------
        print(header("Step 3: Adding entities as composite members..."))

        for artifact_def in ARTIFACTS:
            name = artifact_def["name"]
            position = artifact_def["position"]
            entity_id = entity_ids.get(name)

            if entity_id is None and not dry_run:
                print(skip(f"Skipping member '{name}' — entity ID unknown (creation failed)"))
                continue

            display_id = entity_id or "<pending>"
            member_status = add_member(
                client,
                composite_id,
                display_id if not dry_run else name,
                position,
                api_base,
                dry_run,
                verbose,
            )

            if member_status == "added":
                print(ok(f"Added member '{name}' at position {position}"))
                summary["members_added"] += 1
            elif member_status == "skipped":
                print(skip(f"Member '{name}' already in composite — skipping"))
                summary["members_skipped"] += 1
            elif member_status == "dry_run":
                print(info(f"[DRY RUN] Would add '{name}' as member at position {position}"))
            elif member_status == "error":
                summary["members_failed"] += 1

    _print_summary(summary)

    has_failures = (
        summary["entities_failed"] > 0 or summary["members_failed"] > 0
    )
    return 1 if has_failures else 0


def _print_summary(summary: dict) -> None:
    """Print a formatted summary of what happened during seeding."""
    print(header("=" * 50))
    print(_c(BOLD, "  SEED SUMMARY"))
    print(_c(BOLD, "  " + "=" * 48))
    print(f"\n  Context Entities:")
    print(f"    {_c(GREEN, str(summary['entities_created']))} created")
    print(f"    {_c(YELLOW, str(summary['entities_skipped']))} skipped (already existed)")
    if summary["entities_failed"]:
        print(f"    {_c(RED, str(summary['entities_failed']))} FAILED")

    print(f"\n  Composite:")
    if summary["composite_created"]:
        print(f"    {_c(GREEN, '1')} created")
    elif summary["composite_skipped"]:
        print(f"    {_c(YELLOW, '1')} skipped (already existed)")

    print(f"\n  Memberships:")
    print(f"    {_c(GREEN, str(summary['members_added']))} added")
    print(f"    {_c(YELLOW, str(summary['members_skipped']))} skipped (already existed)")
    if summary["members_failed"]:
        print(f"    {_c(RED, str(summary['members_failed']))} FAILED")

    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed the fin-serv-compliance composite with demo context artifacts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo/seed-composite.py
  python demo/seed-composite.py --api-url http://localhost:8080
  python demo/seed-composite.py --dry-run --verbose
  python demo/seed-composite.py --clean          # wipe and re-seed
  python demo/seed-composite.py --clean --dry-run  # preview clean+seed
        """,
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8080",
        help="SkillMeat API base URL (default: http://localhost:8080)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without making any API calls",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed request/response information",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help=(
            "Delete existing composite and entities before seeding. "
            "Useful for a clean re-seed in development."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    mode_parts = []
    if args.dry_run:
        mode_parts.append(_c(YELLOW, "DRY RUN"))
    if args.clean:
        mode_parts.append(_c(RED, "CLEAN"))
    mode_str = f" [{', '.join(mode_parts)}]" if mode_parts else ""

    print(
        _c(BOLD, f"\nSkillMeat Demo Seeder — fin-serv-compliance{mode_str}")
    )
    print(_c(DIM, f"  API: {args.api_url}"))
    print(_c(DIM, f"  Composite: {COMPOSITE['composite_id']}"))
    print(_c(DIM, f"  Entities: {len(ARTIFACTS)}"))

    # Verify seed directory exists
    if not SEED_BASE.exists():
        print(err(f"Seed directory not found: {SEED_BASE}"))
        print(err("Run this script from the repository root or ensure the seed-artifacts directory exists."))
        sys.exit(1)

    exit_code = seed(
        api_base=args.api_url.rstrip("/"),
        dry_run=args.dry_run,
        verbose=args.verbose,
        clean=args.clean,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
