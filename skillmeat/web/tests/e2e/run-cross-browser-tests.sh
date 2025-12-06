#!/usr/bin/env bash
#
# Cross-Browser Test Runner for DIS-5.9
#
# Runs skip preference persistence tests across Chrome, Firefox, and Safari
# Generates a consolidated report with browser-specific results
#
# Usage:
#   ./tests/e2e/run-cross-browser-tests.sh [--headed] [--ui]
#
# Options:
#   --headed    Run tests in headed mode (show browser windows)
#   --ui        Run tests in Playwright UI mode (interactive)
#   --debug     Run tests in debug mode
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
HEADED=""
UI_MODE=""
DEBUG_MODE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --headed)
      HEADED="--headed"
      shift
      ;;
    --ui)
      UI_MODE="--ui"
      shift
      ;;
    --debug)
      DEBUG_MODE="--debug"
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# Test file
TEST_FILE="tests/e2e/cross-browser-skip-prefs.spec.ts"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cross-Browser Testing for Skip Preferences${NC}"
echo -e "${BLUE}DIS-5.9: LocalStorage Persistence${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if UI mode is enabled
if [ -n "$UI_MODE" ]; then
  echo -e "${YELLOW}Running in UI mode (interactive)...${NC}"
  pnpm test:e2e:ui "$TEST_FILE"
  exit 0
fi

# Check if debug mode is enabled
if [ -n "$DEBUG_MODE" ]; then
  echo -e "${YELLOW}Running in debug mode...${NC}"
  pnpm test:e2e:debug "$TEST_FILE"
  exit 0
fi

# Track results
CHROMIUM_RESULT=0
FIREFOX_RESULT=0
WEBKIT_RESULT=0

# Run Chromium tests
echo -e "${BLUE}Running tests in Chromium (Chrome)...${NC}"
if pnpm test:e2e --project=chromium $HEADED "$TEST_FILE"; then
  echo -e "${GREEN}✓ Chromium tests passed${NC}"
  CHROMIUM_RESULT=1
else
  echo -e "${RED}✗ Chromium tests failed${NC}"
fi
echo ""

# Run Firefox tests
echo -e "${BLUE}Running tests in Firefox...${NC}"
if pnpm test:e2e --project=firefox $HEADED "$TEST_FILE"; then
  echo -e "${GREEN}✓ Firefox tests passed${NC}"
  FIREFOX_RESULT=1
else
  echo -e "${RED}✗ Firefox tests failed${NC}"
fi
echo ""

# Run WebKit tests (Safari)
echo -e "${BLUE}Running tests in WebKit (Safari)...${NC}"
if pnpm test:e2e --project=webkit $HEADED "$TEST_FILE"; then
  echo -e "${GREEN}✓ WebKit tests passed${NC}"
  WEBKIT_RESULT=1
else
  echo -e "${RED}✗ WebKit tests failed${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cross-Browser Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if [ $CHROMIUM_RESULT -eq 1 ]; then
  echo -e "${GREEN}✓ Chromium (Chrome):${NC} PASSED"
else
  echo -e "${RED}✗ Chromium (Chrome):${NC} FAILED"
fi

if [ $FIREFOX_RESULT -eq 1 ]; then
  echo -e "${GREEN}✓ Firefox:${NC} PASSED"
else
  echo -e "${RED}✗ Firefox:${NC} FAILED"
fi

if [ $WEBKIT_RESULT -eq 1 ]; then
  echo -e "${GREEN}✓ WebKit (Safari):${NC} PASSED"
else
  echo -e "${RED}✗ WebKit (Safari):${NC} FAILED"
fi

echo ""

# Overall result
TOTAL_PASSED=$((CHROMIUM_RESULT + FIREFOX_RESULT + WEBKIT_RESULT))

if [ $TOTAL_PASSED -eq 3 ]; then
  echo -e "${GREEN}========================================${NC}"
  echo -e "${GREEN}All browsers passed! (3/3)${NC}"
  echo -e "${GREEN}========================================${NC}"
  exit 0
elif [ $TOTAL_PASSED -eq 0 ]; then
  echo -e "${RED}========================================${NC}"
  echo -e "${RED}All browsers failed! (0/3)${NC}"
  echo -e "${RED}========================================${NC}"
  exit 1
else
  echo -e "${YELLOW}========================================${NC}"
  echo -e "${YELLOW}Partial success: $TOTAL_PASSED/3 browsers passed${NC}"
  echo -e "${YELLOW}========================================${NC}"
  exit 1
fi
