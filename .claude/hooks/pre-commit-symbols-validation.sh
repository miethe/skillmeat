#!/usr/bin/env bash
# Pre-commit hook: Validate symbol files are up-to-date and schema-compliant
#
# Purpose: Ensure symbol files are valid before committing
# Trigger: Pre-commit (automatic) or on-demand validation
#
# Exit codes:
#   0 - Validation passed (or warnings only - allow commit)
#   1 - Validation failed with errors (block commit)
#
# Usage:
#   .claude/hooks/pre-commit-symbols-validation.sh

set -e

# Color codes for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if symbol files are staged
STAGED_SYMBOLS=$(git diff --cached --name-only 2>/dev/null | grep -E '^ai/symbols-.*\.json$' || true)

if [[ -z "$STAGED_SYMBOLS" ]]; then
    # No symbol files staged, skip validation
    exit 0
fi

echo -e "${GREEN}Validating symbol files...${NC}" >&2

# Run symbol validation
python .claude/skills/symbols/scripts/validate_symbols.py 2>&1
VALIDATION_EXIT=$?

# Interpret exit codes:
# 0 = Valid (pass)
# 1 = Warnings only (allow commit but notify)
# 2 = Errors (block commit)

if [[ $VALIDATION_EXIT -eq 0 ]]; then
    echo -e "${GREEN}✓ Symbol validation passed${NC}" >&2
    exit 0
elif [[ $VALIDATION_EXIT -eq 1 ]]; then
    echo "" >&2
    echo -e "${YELLOW}⚠️  Symbol validation completed with warnings (commit allowed)${NC}" >&2
    echo -e "${YELLOW}Consider addressing warnings before pushing.${NC}" >&2
    exit 0
elif [[ $VALIDATION_EXIT -eq 2 ]]; then
    echo "" >&2
    echo -e "${RED}✗ Symbol validation failed with errors${NC}" >&2
    echo -e "${RED}Fix errors above before committing. Run:${NC}" >&2
    echo -e "${RED}  python .claude/skills/symbols/scripts/validate_symbols.py${NC}" >&2
    exit 1
else
    # Unexpected exit code
    echo "" >&2
    echo -e "${RED}✗ Symbol validation exited with unexpected code: $VALIDATION_EXIT${NC}" >&2
    exit 1
fi
