#!/bin/bash
set -e

# SkillMeat - Run All Tests Script
#
# This script runs the complete test suite including:
# - Python unit tests
# - Python integration tests
# - Frontend unit tests (Jest)
# - Frontend E2E tests (Playwright)
#
# Usage:
#   ./scripts/run_all_tests.sh [OPTIONS]
#
# Options:
#   --skip-python     Skip Python tests
#   --skip-frontend   Skip frontend tests
#   --skip-e2e        Skip E2E tests
#   --fast            Run only fast unit tests
#   --coverage        Generate coverage reports
#   --help            Show this help message

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
SKIP_PYTHON=false
SKIP_FRONTEND=false
SKIP_E2E=false
FAST_ONLY=false
WITH_COVERAGE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-python)
            SKIP_PYTHON=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --skip-e2e)
            SKIP_E2E=true
            shift
            ;;
        --fast)
            FAST_ONLY=true
            shift
            ;;
        --coverage)
            WITH_COVERAGE=true
            shift
            ;;
        --help)
            grep "^#" "$0" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}SkillMeat Test Suite Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Track overall status
TESTS_PASSED=true

# ============================================================================
# Python Backend Tests
# ============================================================================
if [ "$SKIP_PYTHON" = false ]; then
    echo -e "${YELLOW}Running Python tests...${NC}"
    echo ""

    # Check if pytest is available
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}pytest not found. Please install dev dependencies:${NC}"
        echo -e "${RED}  pip install -e \".[dev]\"${NC}"
        exit 1
    fi

    if [ "$FAST_ONLY" = true ]; then
        echo -e "${BLUE}Running Python unit tests (fast)...${NC}"
        if [ "$WITH_COVERAGE" = true ]; then
            pytest -v -m "unit" --cov=skillmeat --cov-report=xml --cov-report=html --cov-report=term
        else
            pytest -v -m "unit"
        fi
    else
        echo -e "${BLUE}Running all Python tests...${NC}"
        if [ "$WITH_COVERAGE" = true ]; then
            pytest -v --cov=skillmeat --cov-report=xml --cov-report=html --cov-report=term
        else
            pytest -v
        fi
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Python tests passed${NC}"
    else
        echo -e "${RED}✗ Python tests failed${NC}"
        TESTS_PASSED=false
    fi
    echo ""
else
    echo -e "${YELLOW}Skipping Python tests${NC}"
    echo ""
fi

# ============================================================================
# Frontend Unit Tests (Jest)
# ============================================================================
if [ "$SKIP_FRONTEND" = false ]; then
    echo -e "${YELLOW}Running frontend unit tests...${NC}"
    echo ""

    cd skillmeat/web

    # Check if pnpm is available
    if ! command -v pnpm &> /dev/null; then
        echo -e "${RED}pnpm not found. Please install pnpm:${NC}"
        echo -e "${RED}  npm install -g pnpm${NC}"
        cd ../..
        exit 1
    fi

    # Check if dependencies are installed
    if [ ! -d "node_modules" ]; then
        echo -e "${BLUE}Installing frontend dependencies...${NC}"
        pnpm install --frozen-lockfile
        echo ""
    fi

    echo -e "${BLUE}Running Jest tests...${NC}"
    if [ "$WITH_COVERAGE" = true ]; then
        pnpm test:coverage
    else
        pnpm test
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Frontend unit tests passed${NC}"
    else
        echo -e "${RED}✗ Frontend unit tests failed${NC}"
        TESTS_PASSED=false
    fi
    echo ""

    cd ../..
else
    echo -e "${YELLOW}Skipping frontend unit tests${NC}"
    echo ""
fi

# ============================================================================
# Frontend E2E Tests (Playwright)
# ============================================================================
if [ "$SKIP_E2E" = false ] && [ "$FAST_ONLY" = false ]; then
    echo -e "${YELLOW}Running E2E tests...${NC}"
    echo ""

    cd skillmeat/web

    echo -e "${BLUE}Running Playwright E2E tests...${NC}"
    pnpm test:e2e

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ E2E tests passed${NC}"
    else
        echo -e "${RED}✗ E2E tests failed${NC}"
        TESTS_PASSED=false
    fi
    echo ""

    cd ../..
else
    if [ "$SKIP_E2E" = true ]; then
        echo -e "${YELLOW}Skipping E2E tests${NC}"
    else
        echo -e "${YELLOW}Skipping E2E tests (fast mode)${NC}"
    fi
    echo ""
fi

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Suite Summary${NC}"
echo -e "${BLUE}========================================${NC}"

if [ "$TESTS_PASSED" = true ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""

    if [ "$WITH_COVERAGE" = true ]; then
        echo -e "${BLUE}Coverage reports generated:${NC}"
        echo -e "  Python:   ./htmlcov/index.html"
        echo -e "  Frontend: ./skillmeat/web/coverage/lcov-report/index.html"
        echo ""
    fi

    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo -e "${YELLOW}Please review the test output above for details.${NC}"
    echo ""
    exit 1
fi
