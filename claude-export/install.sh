#!/usr/bin/env bash

# install.sh - Template variable substitution for claude-export
# Replaces {{VARIABLE}} placeholders with values from config/template-config.json
#
# Usage:
#   ./install.sh [options]
#
# Options:
#   --config=FILE         Use custom config file (default: config/template-config.json)
#   --output-dir=DIR      Output to different directory (default: current directory)
#   --dry-run             Show what would be changed without modifying files
#   --validate            Validate config file without applying changes
#   --help                Show this help message
#
# Exit codes:
#   0: Success
#   1: General error
#   2: Config file not found or invalid
#   3: Missing required variables
#   4: File processing error

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Default configuration
CONFIG_FILE="${SCRIPT_DIR}/config/template-config.json"
OUTPUT_DIR="${SCRIPT_DIR}"
DRY_RUN=false
VALIDATE_ONLY=false

# Counters for summary
FILES_PROCESSED=0
FILES_MODIFIED=0
FILES_SKIPPED=0
FILES_BACKED_UP=0
VARIABLES_REPLACED=0
ERRORS_ENCOUNTERED=0

# Arrays to track changes (simple arrays for bash 3.2 compatibility)
PROCESSED_FILES=()
MODIFIED_FILES=()
ERROR_FILES=()
VARIABLE_USAGE_LOG="${SCRIPT_DIR}/.install-variable-usage.tmp"

# Source dependencies (optional, we have fallback)
if [[ -f "$SCRIPT_DIR/scripts/json-utils.sh" ]]; then
    source "$SCRIPT_DIR/scripts/json-utils.sh" 2>/dev/null || true
fi

# ============================================================================
# Helper Functions
# ============================================================================

# Print usage information
print_usage() {
    cat << EOF
${BOLD}claude-export Template Installation Script${NC}

${BOLD}DESCRIPTION${NC}
    Performs template variable substitution in claude-export files, replacing
    {{VARIABLE}} placeholders with actual values from a configuration file.

${BOLD}USAGE${NC}
    $0 [options]

${BOLD}OPTIONS${NC}
    --config=FILE         Use custom config file
                         (default: config/template-config.json)

    --output-dir=DIR      Output to different directory
                         (default: current directory)
                         Files will be written to DIR, not modified in place

    --dry-run            Show what would be changed without modifying files
                         Creates a detailed preview of all substitutions

    --validate           Validate config file without applying changes
                         Checks JSON syntax and required fields

    --help               Show this help message

${BOLD}EXAMPLES${NC}
    # Install with default config
    $0

    # Dry run to preview changes
    $0 --dry-run

    # Use custom config
    $0 --config=my-project-config.json

    # Install to different directory
    $0 --output-dir=/path/to/output

    # Validate config without installing
    $0 --validate --config=my-config.json

${BOLD}EXIT CODES${NC}
    0   Success
    1   General error
    2   Config file not found or invalid
    3   Missing required variables
    4   File processing error

${BOLD}CONFIGURATION${NC}
    See config/template-config.json for all available variables.
    See TEMPLATIZATION_GUIDE.md for comprehensive documentation.

EOF
}

# Print section header
print_header() {
    local title="$1"
    echo ""
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo -e "${BOLD}${BLUE}${title}${NC}"
    echo -e "${BOLD}${BLUE}========================================${NC}"
    echo ""
}

# Print step
print_step() {
    local step="$1"
    echo -e "${CYAN}▸${NC} ${BOLD}${step}${NC}"
}

# Print success
print_success() {
    local message="$1"
    echo -e "${GREEN}✓${NC} ${message}"
}

# Print warning
print_warning() {
    local message="$1"
    echo -e "${YELLOW}⚠${NC} ${message}"
}

# Print error
print_error() {
    local message="$1"
    echo -e "${RED}✗${NC} ${message}" >&2
}

# Print info
print_info() {
    local message="$1"
    echo -e "${BLUE}ℹ${NC} ${message}"
}

# ============================================================================
# Config Validation Functions
# ============================================================================

# Check if jq is available
check_dependencies() {
    print_step "Checking dependencies..."

    if ! command -v jq &> /dev/null; then
        print_error "jq is required but not installed"
        echo "  Install with: brew install jq (macOS) or apt-get install jq (Ubuntu)"
        return 1
    fi

    print_success "Dependencies satisfied (jq available)"
    return 0
}

# Validate config file exists and is valid JSON
validate_config_file() {
    local config_file="$1"

    print_step "Validating configuration file: ${config_file##*/}"

    if [[ ! -f "$config_file" ]]; then
        print_error "Config file not found: $config_file"
        return 2
    fi

    # Validate JSON syntax
    if ! jq empty "$config_file" 2>/dev/null; then
        print_error "Invalid JSON in config file: $config_file"
        return 2
    fi

    print_success "Config file is valid JSON"

    # Check for required top-level keys
    local required_keys=("metadata" "identity" "architecture" "standards" "workflow")
    local missing_keys=()

    for key in "${required_keys[@]}"; do
        if ! jq -e ".$key" "$config_file" > /dev/null 2>&1; then
            missing_keys+=("$key")
        fi
    done

    if [[ ${#missing_keys[@]} -gt 0 ]]; then
        print_error "Missing required top-level keys in config:"
        printf "  - %s\n" "${missing_keys[@]}"
        return 2
    fi

    print_success "All required top-level keys present"

    # Check for required variables
    check_required_variables "$config_file" || return 3

    return 0
}

# Check for required variables
check_required_variables() {
    local config_file="$1"

    print_step "Checking required variables..."

    local required_vars=(
        "identity.PROJECT_NAME.default"
        "architecture.PROJECT_ARCHITECTURE.default"
        "standards.PROJECT_STANDARDS.default"
        "workflow.PM_WORKFLOW.default"
    )

    local missing_vars=()

    for var_path in "${required_vars[@]}"; do
        local value
        value=$(jq -r ".$var_path // \"\"" "$config_file" 2>/dev/null)
        if [[ -z "$value" || "$value" == "null" ]]; then
            missing_vars+=("$var_path")
        fi
    done

    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        print_error "Missing required variable values:"
        printf "  - %s\n" "${missing_vars[@]}"
        return 3
    fi

    print_success "All required variables have values"
    return 0
}

# Extract all variables from config
extract_variables() {
    local config_file="$1"

    print_step "Extracting variables from config..."

    # Use jq to extract all variables with their values
    # This creates a flat key-value structure: VARIABLE_NAME=value
    local vars_json
    vars_json=$(jq -r '
        . as $root |
        [
            # Extract from each category
            (.identity // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.architecture // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.standards // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.workflow // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.documentation // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.observability // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.permissions // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.paths // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.technology // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.examples // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.agents // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key}),
            (.version // {} | to_entries[] | .value | select(type == "object") | {key: .default, value: .key})
        ] |
        map(select(.key != null and .value != null))
    ' "$config_file" 2>/dev/null)

    if [[ -z "$vars_json" || "$vars_json" == "null" || "$vars_json" == "[]" ]]; then
        print_error "Failed to extract variables from config"
        return 1
    fi

    # Count extracted variables
    local var_count
    var_count=$(echo "$vars_json" | jq 'length' 2>/dev/null || echo "0")

    print_success "Extracted $var_count variables from config"

    # Return the JSON array
    echo "$vars_json"
    return 0
}

# ============================================================================
# File Processing Functions
# ============================================================================

# Find all templatized files
find_templatized_files() {
    print_step "Finding templatized files..."

    local source_dir="${1:-$SCRIPT_DIR}"
    local templatized_files=()

    # Directories to search
    local search_dirs=(
        "agents"
        "commands"
        "templates"
        "config"
        "skills"
        "hooks"
    )

    for dir in "${search_dirs[@]}"; do
        local dir_path="$source_dir/$dir"
        if [[ -d "$dir_path" ]]; then
            # Find files containing {{VARIABLE}} patterns
            while IFS= read -r -d '' file; do
                if grep -q '{{[A-Z_]*}}' "$file" 2>/dev/null; then
                    templatized_files+=("$file")
                fi
            done < <(find "$dir_path" -type f \( -name "*.md" -o -name "*.json" -o -name "*.sh" \) -print0)
        fi
    done

    local count=${#templatized_files[@]}
    if [[ $count -eq 0 ]]; then
        print_warning "No templatized files found"
        return 1
    fi

    print_success "Found $count templatized files"

    # Print the files
    printf '%s\n' "${templatized_files[@]}"
    return 0
}

# Replace variables in a single file
process_file() {
    local input_file="$1"
    local variables_json="$2"
    local output_file="$3"

    FILES_PROCESSED=$((FILES_PROCESSED + 1))

    # Read file content
    local content
    content=$(cat "$input_file")

    # Track if any changes were made
    local original_content="$content"
    local changes_made=false

    # Extract all {{VARIABLE}} placeholders from the file
    local placeholders
    placeholders=$(echo "$content" | grep -o '{{[A-Z_]*}}' | sort -u || true)

    if [[ -z "$placeholders" ]]; then
        FILES_SKIPPED=$((FILES_SKIPPED + 1))
        return 0
    fi

    # Replace each placeholder
    while IFS= read -r placeholder; do
        if [[ -z "$placeholder" ]]; then
            continue
        fi

        # Extract variable name (remove {{ and }})
        local var_name="${placeholder#\{\{}"
        var_name="${var_name%\}\}}"

        # Find value in variables JSON
        local var_value
        var_value=$(echo "$variables_json" | jq -r ".[] | select(.value == \"$var_name\") | .key" 2>/dev/null | head -n 1)

        if [[ -z "$var_value" || "$var_value" == "null" ]]; then
            print_warning "No value found for variable: $var_name in ${input_file##*/}"
            continue
        fi

        # Handle special JSON values (objects, arrays)
        if [[ "$var_value" =~ ^\{.*\}$ ]] || [[ "$var_value" =~ ^\[.*\]$ ]]; then
            # For JSON files, replace with minified JSON
            if [[ "$input_file" == *.json ]]; then
                local minified_value
                minified_value=$(echo "$var_value" | jq -c . 2>/dev/null || echo "$var_value")
                content="${content//$placeholder/$minified_value}"
            else
                # For non-JSON files, pretty print
                content="${content//$placeholder/$var_value}"
            fi
        else
            # Simple string replacement
            content="${content//$placeholder/$var_value}"
        fi

        # Track variable usage (log to temp file for summary)
        echo "$var_name" >> "$VARIABLE_USAGE_LOG"
        VARIABLES_REPLACED=$((VARIABLES_REPLACED + 1))
        changes_made=true

    done <<< "$placeholders"

    # Write output if changes were made
    if [[ "$changes_made" == true ]]; then
        if [[ "$DRY_RUN" == false ]]; then
            # Create output directory if needed
            local output_dir
            output_dir=$(dirname "$output_file")
            mkdir -p "$output_dir"

            # Backup original file if in-place modification
            if [[ "$input_file" == "$output_file" ]]; then
                cp "$input_file" "${input_file}.backup"
                FILES_BACKED_UP=$((FILES_BACKED_UP + 1))
            fi

            # Write modified content
            echo "$content" > "$output_file"
        fi

        FILES_MODIFIED=$((FILES_MODIFIED + 1))
        MODIFIED_FILES+=("$input_file")
    else
        FILES_SKIPPED=$((FILES_SKIPPED + 1))
    fi

    return 0
}

# Process all templatized files
process_all_files() {
    local variables_json="$1"

    print_header "Processing Files"

    # Initialize variable usage log
    rm -f "$VARIABLE_USAGE_LOG"
    touch "$VARIABLE_USAGE_LOG"

    # Find all templatized files
    local files
    mapfile -t files < <(find_templatized_files "$SCRIPT_DIR")

    if [[ ${#files[@]} -eq 0 ]]; then
        print_warning "No files to process"
        return 0
    fi

    echo ""
    print_info "Processing ${#files[@]} files..."
    echo ""

    # Process each file
    for input_file in "${files[@]}"; do
        # Determine output file path
        local relative_path="${input_file#$SCRIPT_DIR/}"
        local output_file

        if [[ "$OUTPUT_DIR" == "$SCRIPT_DIR" ]]; then
            # In-place modification
            output_file="$input_file"
        else
            # Output to different directory
            output_file="$OUTPUT_DIR/$relative_path"
        fi

        # Show progress
        if [[ "$DRY_RUN" == true ]]; then
            echo -e "${CYAN}[DRY RUN]${NC} Processing: ${relative_path}"
        else
            echo -e "Processing: ${relative_path}"
        fi

        # Process the file
        if ! process_file "$input_file" "$variables_json" "$output_file"; then
            print_error "Failed to process: $relative_path"
            ERROR_FILES+=("$input_file")
            ERRORS_ENCOUNTERED=$((ERRORS_ENCOUNTERED + 1))
        fi

        PROCESSED_FILES+=("$input_file")
    done

    echo ""
    print_success "File processing complete"
    return 0
}

# ============================================================================
# Summary and Reporting Functions
# ============================================================================

# Print detailed summary
print_summary() {
    print_header "Installation Summary"

    # Files summary
    echo -e "${BOLD}Files:${NC}"
    echo -e "  Total processed:    ${BOLD}${FILES_PROCESSED}${NC}"
    echo -e "  Modified:           ${GREEN}${FILES_MODIFIED}${NC}"
    echo -e "  Skipped (no vars):  ${YELLOW}${FILES_SKIPPED}${NC}"
    echo -e "  Backed up:          ${BLUE}${FILES_BACKED_UP}${NC}"
    if [[ $ERRORS_ENCOUNTERED -gt 0 ]]; then
        echo -e "  Errors:             ${RED}${ERRORS_ENCOUNTERED}${NC}"
    fi
    echo ""

    # Variables summary
    echo -e "${BOLD}Variables:${NC}"
    echo -e "  Total replacements: ${BOLD}${VARIABLES_REPLACED}${NC}"

    # Calculate unique variables from log file
    if [[ -f "$VARIABLE_USAGE_LOG" ]]; then
        local unique_vars
        unique_vars=$(sort "$VARIABLE_USAGE_LOG" | uniq | wc -l | tr -d ' ')
        echo -e "  Unique variables:   ${BOLD}${unique_vars}${NC}"
        echo ""

        # Top 10 most replaced variables
        echo -e "${BOLD}Most Replaced Variables:${NC}"
        sort "$VARIABLE_USAGE_LOG" | uniq -c | sort -rn | head -10 | while read count var; do
            echo -e "  ${CYAN}${var}${NC}: $count times"
        done
        echo ""
    else
        echo ""
    fi

    # Modified files
    if [[ ${#MODIFIED_FILES[@]} -gt 0 ]]; then
        echo -e "${BOLD}Modified Files:${NC}"
        printf '  %s\n' "${MODIFIED_FILES[@]}" | head -20
        if [[ ${#MODIFIED_FILES[@]} -gt 20 ]]; then
            echo -e "  ${YELLOW}... and $((${#MODIFIED_FILES[@]} - 20)) more${NC}"
        fi
        echo ""
    fi

    # Errors
    if [[ ${#ERROR_FILES[@]} -gt 0 ]]; then
        echo -e "${BOLD}${RED}Files with Errors:${NC}"
        printf '  %s\n' "${ERROR_FILES[@]}"
        echo ""
    fi

    # Mode indicator
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${BOLD}${CYAN}DRY RUN MODE${NC}: No files were actually modified"
        echo -e "Run without --dry-run to apply changes"
    else
        echo -e "${BOLD}${GREEN}Installation Complete!${NC}"
        if [[ $FILES_BACKED_UP -gt 0 ]]; then
            echo -e "Original files backed up with .backup extension"
        fi
    fi

    echo ""
}

# ============================================================================
# Main Installation Flow
# ============================================================================

# Parse command-line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --config=*)
                CONFIG_FILE="${1#*=}"
                shift
                ;;
            --output-dir=*)
                OUTPUT_DIR="${1#*=}"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --validate)
                VALIDATE_ONLY=true
                shift
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                echo ""
                print_usage
                exit 1
                ;;
        esac
    done
}

# Main installation function
main() {
    # Parse arguments
    parse_arguments "$@"

    # Print header
    print_header "claude-export Template Installation"

    echo -e "${BOLD}Configuration:${NC}"
    echo -e "  Config file:  ${CONFIG_FILE}"
    echo -e "  Output dir:   ${OUTPUT_DIR}"
    echo -e "  Mode:         $( [[ "$DRY_RUN" == true ]] && echo "${CYAN}DRY RUN${NC}" || echo "${GREEN}INSTALL${NC}" )"
    echo ""

    # Step 1: Check dependencies
    if ! check_dependencies; then
        exit 1
    fi

    # Step 2: Validate config file
    if ! validate_config_file "$CONFIG_FILE"; then
        exit 2
    fi

    # If validate-only mode, exit here
    if [[ "$VALIDATE_ONLY" == true ]]; then
        print_success "Config validation complete"
        exit 0
    fi

    # Step 3: Extract variables
    local variables_json
    if ! variables_json=$(extract_variables "$CONFIG_FILE"); then
        print_error "Failed to extract variables"
        exit 2
    fi

    # Step 4: Process files
    if ! process_all_files "$variables_json"; then
        print_error "File processing failed"
        exit 4
    fi

    # Step 5: Print summary
    print_summary

    # Cleanup temporary files
    rm -f "$VARIABLE_USAGE_LOG"

    # Exit with error if any errors encountered
    if [[ $ERRORS_ENCOUNTERED -gt 0 ]]; then
        exit 4
    fi

    exit 0
}

# Run main function
main "$@"
