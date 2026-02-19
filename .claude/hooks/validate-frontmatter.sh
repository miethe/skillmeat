#!/usr/bin/env bash
# Validate staged markdown frontmatter for project planning and tracking docs.
# - Warn (non-blocking) when schema_version/doc_type are missing.
# - Block only on broken YAML or invalid required field values.

set -euo pipefail

TARGET_PATTERN='^(docs/project_plans/|\.claude/progress/|\.claude/worknotes/)'
VALIDATOR=".claude/skills/artifact-tracking/scripts/validate_artifact.py"

if [[ ! -f "$VALIDATOR" ]]; then
  echo "Warning: validator script not found: $VALIDATOR" >&2
  exit 0
fi

STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM -- '*.md' || true)
if [[ -z "${STAGED_FILES}" ]]; then
  exit 0
fi

WARNINGS=0
ERRORS=0

while IFS= read -r file; do
  [[ -z "$file" ]] && continue
  [[ "$file" =~ $TARGET_PATTERN ]] || continue
  [[ -f "$file" ]] || continue

  INSPECT_OUTPUT=$(python - "$file" <<'PY'
import re
import sys
from pathlib import Path

import yaml

path = Path(sys.argv[1])
content = path.read_text(encoding="utf-8")

if not content.startswith("---\n"):
    print("NO_FRONTMATTER")
    sys.exit(0)

match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
if not match:
    print("YAML_ERROR:Could not find closing frontmatter delimiter")
    sys.exit(0)

try:
    meta = yaml.safe_load(match.group(1)) or {}
except Exception as exc:
    print(f"YAML_ERROR:{exc}")
    sys.exit(0)

if not isinstance(meta, dict):
    print("YAML_ERROR:Frontmatter must be a mapping")
    sys.exit(0)

has_schema = "1" if "schema_version" in meta else "0"
has_doc_type = "1" if "doc_type" in meta else "0"

doc_type = meta.get("doc_type")
legacy_type = meta.get("type")

artifact_type = ""
if isinstance(doc_type, str):
    mapping = {
        "progress": "progress",
        "context": "context",
        "bug_fix": "bug-fix",
        "observation": "observation",
        "prd": "prd",
        "implementation_plan": "implementation-plan",
        "phase_plan": "phase-plan",
        "spike": "spike",
        "quick_feature": "quick-feature",
        "report": "report",
    }
    artifact_type = mapping.get(doc_type, "")

if not artifact_type and isinstance(legacy_type, str):
    mapping = {
        "progress": "progress",
        "context": "context",
        "bug-fixes": "bug-fix",
        "observations": "observation",
        "quick-feature-plan": "quick-feature",
    }
    artifact_type = mapping.get(legacy_type, "")

print(f"OK|{artifact_type}|{has_schema}|{has_doc_type}")
PY
)

  if [[ "$INSPECT_OUTPUT" == YAML_ERROR:* ]]; then
    echo "✗ $file has invalid YAML frontmatter: ${INSPECT_OUTPUT#YAML_ERROR:}" >&2
    ERRORS=$((ERRORS + 1))
    continue
  fi

  if [[ "$INSPECT_OUTPUT" == "NO_FRONTMATTER" ]]; then
    echo "⚠ $file has no YAML frontmatter (skipping schema validation)" >&2
    WARNINGS=$((WARNINGS + 1))
    continue
  fi

  IFS='|' read -r _ artifact_type has_schema has_doc_type <<< "$INSPECT_OUTPUT"

  if [[ "$has_schema" == "0" ]]; then
    echo "⚠ $file missing schema_version" >&2
    WARNINGS=$((WARNINGS + 1))
  fi

  if [[ "$has_doc_type" == "0" ]]; then
    echo "⚠ $file missing doc_type" >&2
    WARNINGS=$((WARNINGS + 1))
  fi

  if [[ -z "$artifact_type" ]]; then
    echo "⚠ $file doc type not recognized; skipping strict schema validation" >&2
    WARNINGS=$((WARNINGS + 1))
    continue
  fi

  if ! python "$VALIDATOR" -f "$file" --artifact-type "$artifact_type" >/dev/null; then
    echo "✗ $file failed schema validation for artifact-type '$artifact_type'" >&2
    ERRORS=$((ERRORS + 1))
  fi
done <<< "$STAGED_FILES"

if [[ $ERRORS -gt 0 ]]; then
  echo "Frontmatter validation failed with $ERRORS blocking error(s)." >&2
  exit 1
fi

if [[ $WARNINGS -gt 0 ]]; then
  echo "Frontmatter validation completed with $WARNINGS warning(s)." >&2
fi

exit 0
