#!/usr/bin/env python3
"""
Batch update monthly bug-fixes doc and mark request-log items done.

Usage:
  .claude/scripts/update-bug-docs.py --commits <sha[,sha]> [--req-log REQ-...] [--req-items ID,ID]
  .claude/scripts/update-bug-docs.py --commits <sha[,sha]> --req-log <doc-path> --mark-all-open
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, List, Optional, Sequence, Tuple


REQ_DOC_RE = re.compile(r"\bREQ-\d{8}-[a-z0-9-]+(?:\.md)?\b")
REQ_ITEM_RE = re.compile(r"\bREQ-\d{8}-[a-z0-9-]+-\d{2}\b")


def run(cmd: Sequence[str], *, input_text: Optional[str] = None) -> str:
    result = subprocess.run(
        cmd,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        message = f"Command failed: {' '.join(cmd)}"
        if stderr:
            message += f"\n{stderr}"
        if stdout:
            message += f"\n{stdout}"
        raise RuntimeError(message)
    return result.stdout.strip()


def parse_commits(raw: str) -> List[str]:
    commits = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            commits.append(part)
    return commits


def git_commit_date(commit: str) -> str:
    return run(["git", "show", "-s", "--format=%cs", commit])


def git_commit_message(commit: str) -> str:
    return run(["git", "show", "-s", "--format=%B", commit])


def find_req_ids_from_messages(messages: Iterable[str]) -> Tuple[Optional[str], List[str]]:
    item_ids = []
    doc_ids = []
    for message in messages:
        item_ids.extend(REQ_ITEM_RE.findall(message))
        doc_ids.extend(REQ_DOC_RE.findall(message))

    item_ids = sorted(set(item_ids))

    # Derive doc IDs from item IDs (REQ-...-XX -> REQ-...)
    derived_doc_ids = {re.sub(r"-\d{2}$", "", item_id) for item_id in item_ids}
    doc_ids = sorted(set(doc_ids) | derived_doc_ids)

    # Remove doc_ids that are actually item IDs with .md suffix
    doc_ids = [doc_id.replace(".md", "") for doc_id in doc_ids]

    if len(doc_ids) == 1:
        return doc_ids[0], item_ids
    return None, item_ids


def normalize_req_log_display(req_log: Optional[str]) -> Optional[str]:
    if not req_log:
        return None
    name = Path(req_log).name
    if name.endswith(".md"):
        name = name[:-3]
    return name


def resolve_bug_fixes_path(date_str: str, explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit)
    year, month, _ = date_str.split("-")
    return Path(".claude/worknotes/fixes") / f"bug-fixes-{year}-{month}.md"


def select_items(
    items: Sequence[dict],
    item_ids: Sequence[str],
    mark_all_open: bool,
) -> List[dict]:
    if item_ids:
        item_id_set = set(item_ids)
        return [item for item in items if item.get("id") in item_id_set]
    if not mark_all_open:
        return []
    return [item for item in items if item.get("status") not in {"done", "wontfix"}]


def summarize_notes(notes: str) -> str:
    if not notes:
        return ""
    first_paragraph = notes.strip().split("\n\n")[0]
    return first_paragraph.splitlines()[0].strip()


def build_section(
    *,
    req_log_display: Optional[str],
    commits: Sequence[str],
    date_fixed: str,
    items: Sequence[dict],
) -> str:
    header_title = f"{req_log_display} Fixes ({date_fixed})" if req_log_display else f"Bug Fixes ({date_fixed})"
    lines = ["---", "", f"## {header_title}", "", f"**Commit(s)**: {', '.join(commits)}"]
    if req_log_display:
        lines.append(f"**Request Log**: {req_log_display}")

    for item in items:
        title = item.get("title", "Untitled fix")
        priority = item.get("priority", "medium")
        domain = item.get("domain", "unknown")
        context = item.get("context")
        component = f"{domain}/{context}" if context else domain
        notes = (item.get("notes") or "").strip()
        issue_line = summarize_notes(notes)

        lines.extend(
            [
                "",
                f"### {title}",
                "",
                f"**Date Fixed**: {date_fixed}",
                f"**Severity**: {priority}",
                f"**Component**: {component}",
                f"**Request Log Item**: {item.get('id', 'unknown')}",
            ]
        )
        if issue_line:
            lines.append("")
            lines.append(f"**Issue**: {issue_line}")
        if notes:
            lines.append("")
            lines.append("**Notes**:")
            lines.append(notes)
        lines.append("")
        lines.append("**Status**: RESOLVED")

    return "\n".join(lines).rstrip() + "\n"


def update_bug_fixes_file(path: Path, section: str, commits: Sequence[str], force: bool) -> bool:
    content = path.read_text()
    if not force and any(commit in content for commit in commits):
        return False
    updated = content.rstrip() + "\n\n" + section
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(updated)
    os.replace(temp_path, path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Update bug-fixes doc and request-log items.")
    parser.add_argument("--commits", required=True, help="Comma-separated commit SHAs")
    parser.add_argument("--req-log", help="Request log doc id or path (REQ-YYYYMMDD-... or /path/REQ-....md)")
    parser.add_argument("--req-items", help="Comma-separated request-log item IDs")
    parser.add_argument(
        "--mark-all-open",
        action="store_true",
        help="Mark all non-done items in the request log as done when item IDs are not provided",
    )
    parser.add_argument("--bug-fixes-file", help="Path to bug-fixes-YYYY-MM.md")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without modifying files")
    parser.add_argument("--force", action="store_true", help="Append even if commits already recorded")
    args = parser.parse_args()

    commits = parse_commits(args.commits)
    if not commits:
        print("No commits provided.", file=sys.stderr)
        return 2

    commit_dates = [git_commit_date(commit) for commit in commits]
    date_fixed = commit_dates[0]

    commit_messages = [git_commit_message(commit) for commit in commits]
    req_log_from_commits, item_ids_from_commits = find_req_ids_from_messages(commit_messages)

    req_log = args.req_log or req_log_from_commits
    req_log_display = normalize_req_log_display(req_log)

    req_items = []
    if args.req_items:
        req_items = [item.strip() for item in args.req_items.split(",") if item.strip()]
    elif item_ids_from_commits:
        req_items = item_ids_from_commits

    items_for_doc: List[dict] = []
    if req_log:
        raw = run(["meatycapture", "log", "view", req_log, "--json"])
        log_doc = json.loads(raw)
        items_for_doc = select_items(log_doc.get("items", []), req_items, args.mark_all_open or not req_items)

    bug_fixes_path = resolve_bug_fixes_path(date_fixed, args.bug_fixes_file)
    if not bug_fixes_path.exists():
        print(f"Bug-fixes file not found: {bug_fixes_path}", file=sys.stderr)
        return 2

    section = build_section(
        req_log_display=req_log_display,
        commits=commits,
        date_fixed=date_fixed,
        items=items_for_doc,
    )

    if args.dry_run:
        print(section)
        return 0

    file_updated = update_bug_fixes_file(bug_fixes_path, section, commits, args.force)
    if file_updated:
        print(f"Updated bug-fixes: {bug_fixes_path}")
    else:
        print(f"Bug-fixes already contains commit(s); skipped: {bug_fixes_path}")

    if req_log and items_for_doc:
        for item in items_for_doc:
            item_id = item.get("id")
            if not item_id:
                continue
            run(["meatycapture", "log", "item", "update", req_log, item_id, "--status", "done"])
            run(
                [
                    "meatycapture",
                    "log",
                    "note",
                    "add",
                    req_log,
                    item_id,
                    "--content",
                    f"Fixed in commits: {', '.join(commits)}",
                    "--type",
                    "Bug Fix Attempt",
                ]
            )
        print(f"Updated request-log items: {req_log_display}")
    elif req_log:
        print(f"No request-log items updated for: {req_log_display}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
