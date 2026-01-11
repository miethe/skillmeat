#!/bin/bash

set -euo pipefail

usage() {
  cat <<'USAGE'
Usage: .claude/scripts/batch-file-bugs.sh --input <file|-> [options]

Options:
  --input <path|->       JSON or CSV file path, or "-" for stdin (required)
  --project <slug>       Project slug (default: skillmeat)
  --title <string>       Optional request-log document title
  --domain <string>      Default domain if missing in input
  --type <string>        Default type (default: bug)
  --priority <string>    Default priority (low|medium|high|critical)
  --status <string>      Default status (triage|backlog|planned|in-progress|done|wontfix)
  --context <string>     Default context if missing in input
  --tags <csv>           Default tags (comma-separated)
  --append <doc-path>    Append items to existing request log document
  --dry-run              Print JSON payload instead of calling meatycapture
  -h, --help             Show help

Input format:
  - JSON array of item objects or JSON object with "items"
  - CSV with headers: title,type,domain,context,priority,status,tags,notes,severity,component
USAGE
}

PROJECT="skillmeat"
INPUT=""
DOC_TITLE=""
DEFAULT_DOMAIN=""
DEFAULT_TYPE="bug"
DEFAULT_PRIORITY=""
DEFAULT_STATUS=""
DEFAULT_CONTEXT=""
DEFAULT_TAGS=""
APPEND_DOC=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2 ;;
    --project) PROJECT="$2"; shift 2 ;;
    --title) DOC_TITLE="$2"; shift 2 ;;
    --domain) DEFAULT_DOMAIN="$2"; shift 2 ;;
    --type) DEFAULT_TYPE="$2"; shift 2 ;;
    --priority) DEFAULT_PRIORITY="$2"; shift 2 ;;
    --status) DEFAULT_STATUS="$2"; shift 2 ;;
    --context) DEFAULT_CONTEXT="$2"; shift 2 ;;
    --tags) DEFAULT_TAGS="$2"; shift 2 ;;
    --append) APPEND_DOC="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
done

if [[ -z "$INPUT" ]]; then
  echo "Error: --input is required." >&2
  usage
  exit 2
fi

payload="$(python3 - "$INPUT" "$PROJECT" "$DOC_TITLE" "$DEFAULT_DOMAIN" "$DEFAULT_TYPE" \
  "$DEFAULT_PRIORITY" "$DEFAULT_STATUS" "$DEFAULT_CONTEXT" "$DEFAULT_TAGS" <<'PY'
import csv
import json
import sys
from pathlib import Path

input_path = sys.argv[1]
project = sys.argv[2]
doc_title = sys.argv[3]
default_domain = sys.argv[4]
default_type = sys.argv[5]
default_priority = sys.argv[6]
default_status = sys.argv[7]
default_context = sys.argv[8]
default_tags = sys.argv[9]

def die(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)

def normalize_tags(value: str):
    if not value:
        return None
    tags = [tag.strip() for tag in value.split(",") if tag.strip()]
    return tags or None

def build_item(raw: dict) -> dict:
    title = (raw.get("title") or "").strip()
    if not title:
        die("Missing required field: title")

    item_type = (raw.get("type") or default_type).strip()
    domain = (raw.get("domain") or default_domain).strip()
    context = (raw.get("context") or default_context).strip()
    priority = (raw.get("priority") or raw.get("severity") or default_priority).strip()
    status = (raw.get("status") or default_status).strip()
    tags_value = raw.get("tags") or default_tags
    notes = (raw.get("notes") or "").strip()

    if not domain:
        component = (raw.get("component") or "").strip()
        if component and "/" in component:
            domain = component.split("/", 1)[0]
            context = context or component.split("/", 1)[1]
        else:
            die("Missing required field: domain (or provide --domain)")

    item = {
        "title": title,
        "type": item_type,
        "domain": domain,
    }

    if context:
        item["context"] = context
    if priority:
        item["priority"] = priority
    if status:
        item["status"] = status
    tags = normalize_tags(tags_value)
    if tags:
        item["tags"] = tags
    if notes:
        item["notes"] = notes

    return item

def load_input(path: str) -> list:
    if path == "-":
        data = sys.stdin.read()
        if not data.strip():
            die("No input provided on stdin.")
        content = data
    else:
        content = Path(path).read_text()

    stripped = content.lstrip()
    if stripped.startswith("{") or stripped.startswith("["):
        payload = json.loads(content)
        if isinstance(payload, dict):
            items = payload.get("items", [])
        else:
            items = payload
        if not isinstance(items, list):
            die("JSON input must be a list or an object with an 'items' list.")
        return items

    reader = csv.DictReader(content.splitlines())
    return list(reader)

items_raw = load_input(input_path)
items = [build_item(raw) for raw in items_raw]

doc = {"project": project, "items": items}
if doc_title:
    doc["title"] = doc_title

print(json.dumps(doc, indent=2))
PY
)"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "$payload"
  exit 0
fi

if [[ -n "$APPEND_DOC" ]]; then
  echo "$payload" | meatycapture log append "$APPEND_DOC" --json
else
  echo "$payload" | meatycapture log create --json
fi
