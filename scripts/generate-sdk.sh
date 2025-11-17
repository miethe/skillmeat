#!/usr/bin/env bash
# Generate TypeScript SDK from OpenAPI specification
#
# This script:
# 1. Starts the FastAPI server temporarily
# 2. Exports the OpenAPI specification to JSON
# 3. Generates TypeScript SDK using openapi-typescript-codegen
# 4. Formats the generated code
# 5. Cleans up

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
API_DIR="$PROJECT_ROOT/skillmeat/api"
WEB_DIR="$PROJECT_ROOT/skillmeat/web"
OPENAPI_FILE="$API_DIR/openapi.json"
SDK_OUTPUT_DIR="$WEB_DIR/sdk"

echo -e "${GREEN}Starting SDK generation...${NC}"

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
echo "Checking prerequisites..."

if ! command_exists python3 && ! command_exists python; then
    echo -e "${RED}Error: Python is not installed${NC}"
    exit 1
fi

PYTHON_CMD=$(command_exists python3 && echo "python3" || echo "python")

# Check if skillmeat is installed
if ! $PYTHON_CMD -c "import skillmeat" 2>/dev/null; then
    echo -e "${YELLOW}Warning: skillmeat package not installed. Installing in development mode...${NC}"
    cd "$PROJECT_ROOT"
    pip install -e . >/dev/null 2>&1 || {
        echo -e "${RED}Error: Failed to install skillmeat${NC}"
        exit 1
    }
fi

# Check if pnpm is installed
if ! command_exists pnpm; then
    echo -e "${RED}Error: pnpm is not installed. Install it with: npm install -g pnpm${NC}"
    exit 1
fi

# Ensure web dependencies are installed
echo "Checking web dependencies..."
cd "$WEB_DIR"
if [ ! -d "node_modules" ] || [ ! -d "node_modules/openapi-typescript-codegen" ]; then
    echo "Installing web dependencies..."
    pnpm install
fi

# Generate OpenAPI specification
echo "Generating OpenAPI specification..."
cd "$PROJECT_ROOT"

# Use Python to generate the spec
$PYTHON_CMD -c "
from skillmeat.api.server import create_app
from skillmeat.api.openapi import export_openapi_spec
from pathlib import Path

# Create app
app = create_app()

# Export OpenAPI spec
output_path = Path('$OPENAPI_FILE')
export_openapi_spec(app, output_path, api_version='v1', pretty=True)
print(f'OpenAPI spec exported to: {output_path}')
"

if [ ! -f "$OPENAPI_FILE" ]; then
    echo -e "${RED}Error: Failed to generate OpenAPI specification${NC}"
    exit 1
fi

echo -e "${GREEN}OpenAPI specification generated at: $OPENAPI_FILE${NC}"

# Generate TypeScript SDK
echo "Generating TypeScript SDK..."
cd "$WEB_DIR"

# Remove existing SDK directory to ensure clean generation
if [ -d "$SDK_OUTPUT_DIR" ]; then
    echo "Removing existing SDK directory..."
    rm -rf "$SDK_OUTPUT_DIR"
fi

# Run openapi-typescript-codegen
pnpm run generate-sdk

if [ ! -d "$SDK_OUTPUT_DIR" ]; then
    echo -e "${RED}Error: Failed to generate TypeScript SDK${NC}"
    exit 1
fi

echo -e "${GREEN}TypeScript SDK generated at: $SDK_OUTPUT_DIR${NC}"

# Format generated code
echo "Formatting generated SDK..."
cd "$WEB_DIR"
pnpm run format --loglevel silent || {
    echo -e "${YELLOW}Warning: Failed to format SDK (continuing anyway)${NC}"
}

# Verify TypeScript compilation
echo "Verifying TypeScript compilation..."
cd "$WEB_DIR"
pnpm run type-check || {
    echo -e "${YELLOW}Warning: TypeScript compilation has errors${NC}"
}

# Get SDK version from OpenAPI spec
SDK_VERSION=$(grep -m 1 '"version"' "$OPENAPI_FILE" | cut -d'"' -f4)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SDK Generation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "SDK Version: $SDK_VERSION"
echo "OpenAPI Spec: $OPENAPI_FILE"
echo "SDK Output: $SDK_OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "  1. Review the generated SDK in $SDK_OUTPUT_DIR"
echo "  2. Import the SDK in your components: import { SkillMeatClient } from '@/sdk'"
echo "  3. Use the API client wrapper: import { apiClient } from '@/lib/api-client'"
echo ""
