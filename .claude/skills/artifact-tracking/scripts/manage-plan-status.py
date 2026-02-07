#!/usr/bin/env python3
"""
Manage status fields in PRD and implementation plan frontmatter.

This script provides operations for reading, updating, and querying plan status
across PRD and implementation plan documents.

Usage:
    # Read status from a plan
    python manage-plan-status.py --read docs/project_plans/PRDs/features/my-feature.md

    # Update status
    python manage-plan-status.py --file docs/project_plans/PRDs/features/my-feature.md --status approved

    # Query plans by status
    python manage-plan-status.py --query --status draft --type prd
    python manage-plan-status.py --query --status in-progress --type implementation
    python manage-plan-status.py --query --status completed --type all
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


# Valid status values
VALID_STATUSES = ['draft', 'approved', 'in-progress', 'completed', 'superseded']

# Plan type directory patterns
PLAN_DIRECTORIES = {
    'prd': 'docs/project_plans/PRDs/features',
    'implementation': 'docs/project_plans/implementation_plans/features',
}


def extract_frontmatter_and_body(filepath: Path) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Extract YAML frontmatter and markdown body separately.

    Args:
        filepath: Path to plan file

    Returns:
        Tuple of (frontmatter dict, markdown body string)
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check if content starts with frontmatter delimiter
        if not content.strip().startswith('---'):
            print(f"Error: File does not contain YAML frontmatter", file=sys.stderr)
            return None, ""

        # Find the closing delimiter (second ---)
        match = re.match(r'^---\n(.*?\n)---\n(.*)$', content, re.DOTALL)
        if not match:
            print(f"Error: Could not parse YAML frontmatter", file=sys.stderr)
            return None, ""

        frontmatter_str = match.group(1)
        body = match.group(2)

        frontmatter = yaml.safe_load(frontmatter_str)
        return frontmatter, body

    except Exception as e:
        print(f"Error: Could not read {filepath}: {e}", file=sys.stderr)
        return None, ""


def write_frontmatter_and_body(
    filepath: Path,
    frontmatter: Dict[str, Any],
    body: str
) -> None:
    """
    Write updated frontmatter and preserved body back to file.

    Args:
        filepath: Path to plan file
        frontmatter: Updated frontmatter dictionary
        body: Preserved markdown body
    """
    try:
        # Dump frontmatter to YAML string
        frontmatter_yaml = yaml.dump(
            frontmatter,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        # Write file with frontmatter delimiters
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('---\n')
            f.write(frontmatter_yaml)
            f.write('---\n')
            f.write(body)

    except Exception as e:
        print(f"Error: Could not write to {filepath}: {e}", file=sys.stderr)
        raise


def read_status(filepath: Path) -> Optional[str]:
    """
    Read and print status from plan frontmatter.

    Args:
        filepath: Path to plan file

    Returns:
        Status string if found, None otherwise
    """
    if not filepath.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return None

    frontmatter, _ = extract_frontmatter_and_body(filepath)
    if frontmatter is None:
        return None

    status = frontmatter.get('status')
    title = frontmatter.get('title', filepath.name)
    created = frontmatter.get('created', 'unknown')

    print(f"File: {filepath}")
    print(f"Title: {title}")
    print(f"Status: {status or 'not set'}")
    print(f"Created: {created}")

    return status


def update_status(filepath: Path, status: str) -> bool:
    """
    Update status field in plan frontmatter.

    Args:
        filepath: Path to plan file
        status: New status value

    Returns:
        True if successful, False otherwise
    """
    # Validate status
    if status not in VALID_STATUSES:
        print(
            f"Error: Invalid status '{status}'. Must be one of: {', '.join(VALID_STATUSES)}",
            file=sys.stderr
        )
        return False

    # Check file exists
    if not filepath.exists():
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        return False

    # Extract frontmatter and body
    frontmatter, body = extract_frontmatter_and_body(filepath)
    if frontmatter is None:
        return False

    # Get old status
    old_status = frontmatter.get('status', 'not set')

    # Update status
    frontmatter['status'] = status

    # Update modified timestamp if it exists
    if 'modified' in frontmatter or 'updated' in frontmatter:
        timestamp_key = 'modified' if 'modified' in frontmatter else 'updated'
        frontmatter[timestamp_key] = datetime.now().strftime('%Y-%m-%d')

    # Write back to file
    try:
        write_frontmatter_and_body(filepath, frontmatter, body)
        print(f"✓ Updated status: {old_status} → {status}")
        print(f"  File: {filepath}")
        return True
    except Exception:
        return False


def query_plans(status: Optional[str] = None, plan_type: str = 'all') -> List[Dict[str, Any]]:
    """
    Query plans by status and/or type.

    Args:
        status: Status to filter by (optional)
        plan_type: Type of plans to query ('prd', 'implementation', 'all')

    Returns:
        List of plan metadata dictionaries
    """
    results = []

    # Determine which directories to search
    if plan_type == 'all':
        search_dirs = PLAN_DIRECTORIES.items()
    elif plan_type in PLAN_DIRECTORIES:
        search_dirs = [(plan_type, PLAN_DIRECTORIES[plan_type])]
    else:
        print(f"Error: Invalid plan type '{plan_type}'", file=sys.stderr)
        return []

    # Search each directory
    for plan_type_name, dir_path in search_dirs:
        plan_dir = Path(dir_path)
        if not plan_dir.exists():
            continue

        # Find all markdown files
        for plan_file in plan_dir.glob('*.md'):
            # Silently skip files without valid frontmatter during query
            try:
                with open(plan_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                if not content.strip().startswith('---'):
                    continue

                match = re.match(r'^---\n(.*?\n)---\n(.*)$', content, re.DOTALL)
                if not match:
                    continue

                frontmatter_str = match.group(1)
                frontmatter = yaml.safe_load(frontmatter_str)
            except Exception:
                # Skip files that can't be parsed
                continue

            plan_status = frontmatter.get('status')

            # Filter by status if specified
            if status is not None and plan_status != status:
                continue

            # Extract metadata (convert dates to strings for JSON serialization)
            created = frontmatter.get('created', 'unknown')
            if hasattr(created, 'isoformat'):  # datetime.date or datetime.datetime
                created = created.isoformat()
            elif not isinstance(created, str):
                created = str(created)

            results.append({
                'file': str(plan_file),
                'title': frontmatter.get('title', plan_file.name),
                'status': plan_status or 'not set',
                'created': created,
                'type': plan_type_name
            })

    return results


def main():
    """Main entry point for manage-plan-status script."""
    parser = argparse.ArgumentParser(
        description="Manage status fields in PRD and implementation plan frontmatter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Read status from a plan
  python manage-plan-status.py --read docs/project_plans/PRDs/features/my-feature.md

  # Update status
  python manage-plan-status.py --file docs/project_plans/PRDs/features/my-feature.md --status approved

  # Query plans by status
  python manage-plan-status.py --query --status draft --type prd
  python manage-plan-status.py --query --status in-progress --type implementation
  python manage-plan-status.py --query --status completed --type all

Valid statuses: draft, approved, in-progress, completed, superseded
Valid types: prd, implementation, all
        """
    )

    # Operation modes
    operation_group = parser.add_mutually_exclusive_group(required=False)
    operation_group.add_argument(
        '--read',
        type=Path,
        metavar='FILE',
        help='Read and print status from plan file'
    )
    operation_group.add_argument(
        '--query',
        action='store_true',
        help='Query plans by status and/or type'
    )

    # Update operation arguments
    parser.add_argument(
        '--file',
        '-f',
        type=Path,
        help='Path to plan file (required for update with --status)'
    )
    parser.add_argument(
        '--status',
        '-s',
        choices=VALID_STATUSES,
        help='Status value (for update or query filter)'
    )

    # Query filtering arguments
    parser.add_argument(
        '--type',
        '-t',
        choices=['prd', 'implementation', 'all'],
        default='all',
        help='Plan type to query (default: all)'
    )

    args = parser.parse_args()

    try:
        # Read operation
        if args.read:
            status = read_status(args.read)
            sys.exit(0 if status is not None else 1)

        # Query operation
        elif args.query:
            results = query_plans(status=args.status, plan_type=args.type)
            print(json.dumps(results, indent=2))
            sys.exit(0)

        # Update operation (--file and --status, but not --read or --query)
        elif args.file and args.status:
            success = update_status(args.file, args.status)
            sys.exit(0 if success else 1)

        # Missing required arguments
        elif args.file:
            print("Error: --status is required when using --file for update", file=sys.stderr)
            sys.exit(1)
        elif args.status:
            print("Error: --file is required when using --status for update (or use --query to filter by status)", file=sys.stderr)
            sys.exit(1)
        else:
            print("Error: Must specify --read, --query, or --file with --status", file=sys.stderr)
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
