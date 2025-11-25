#!/bin/bash
# Helper script to run Entity Lifecycle E2E tests
# Usage: ./run-entity-tests.sh [options]
#
# Options:
#   --headed        Run tests in headed mode (visible browser)
#   --debug         Run tests in debug mode
#   --ui            Run tests with Playwright UI
#   --chromium      Run tests only in Chromium
#   --update        Update snapshots (if any)
#   --grep PATTERN  Run only tests matching pattern

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Entity Lifecycle E2E Tests ===${NC}"
echo ""

# Change to web directory
cd "$(dirname "$0")/../.."

# Parse arguments
MODE="normal"
BROWSER=""
GREP=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --headed)
      MODE="headed"
      shift
      ;;
    --debug)
      MODE="debug"
      shift
      ;;
    --ui)
      MODE="ui"
      shift
      ;;
    --chromium)
      BROWSER="--project=chromium"
      shift
      ;;
    --update)
      UPDATE="--update-snapshots"
      shift
      ;;
    --grep)
      GREP="--grep \"$2\""
      shift 2
      ;;
    *)
      echo -e "${YELLOW}Unknown option: $1${NC}"
      shift
      ;;
  esac
done

# Build test command
TEST_FILE="tests/e2e/entity-lifecycle.spec.ts"
BASE_CMD="npx playwright test $TEST_FILE"

case $MODE in
  headed)
    echo -e "${GREEN}Running in headed mode...${NC}"
    CMD="$BASE_CMD --headed $BROWSER $GREP"
    ;;
  debug)
    echo -e "${GREEN}Running in debug mode...${NC}"
    CMD="$BASE_CMD --debug $BROWSER $GREP"
    ;;
  ui)
    echo -e "${GREEN}Running with Playwright UI...${NC}"
    CMD="$BASE_CMD --ui"
    ;;
  *)
    echo -e "${GREEN}Running in headless mode...${NC}"
    CMD="$BASE_CMD $BROWSER $GREP $UPDATE"
    ;;
esac

# Display command
echo -e "${BLUE}Command: $CMD${NC}"
echo ""

# Run tests
eval $CMD

# Show results
echo ""
echo -e "${GREEN}=== Tests Complete ===${NC}"
echo -e "${BLUE}View detailed report: npm run test:report${NC}"
