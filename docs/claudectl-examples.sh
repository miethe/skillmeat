#!/bin/bash
# claudectl Scripting Examples
#
# This file contains example scripts for common automation scenarios.
# These examples demonstrate proper error handling, JSON parsing with jq,
# and integration with CI/CD pipelines.
#
# Usage: Source this file or copy individual functions into your scripts
#   source docs/claudectl-examples.sh
#   deploy_bundle /path/to/project

#==============================================================================
# EXAMPLE 1: Deploy Bundle in CI/CD
#==============================================================================
# Deploy a predefined set of artifacts to a project with error handling

deploy_bundle() {
    local project_path="$1"
    local artifacts=("canvas-design" "pdf-tools" "code-review")

    if [[ -z "$project_path" ]]; then
        echo "Usage: deploy_bundle <project_path>" >&2
        return 1
    fi

    if [[ ! -d "$project_path" ]]; then
        echo "Error: Project directory not found: $project_path" >&2
        return 1
    fi

    echo "Deploying artifacts to $project_path..."

    for artifact in "${artifacts[@]}"; do
        echo "  Deploying $artifact..."
        if ! claudectl deploy "$artifact" --project "$project_path" --force --format json >/dev/null 2>&1; then
            echo "  Failed to deploy $artifact" >&2
            return 1
        fi
    done

    echo "All artifacts deployed successfully"
    return 0
}

# Usage: deploy_bundle /path/to/project

#==============================================================================
# EXAMPLE 2: Check Deployment Status with JSON Parsing
#==============================================================================
# Verify all expected artifacts are deployed using jq for JSON parsing

check_deployments() {
    local expected_artifacts=("$@")
    local missing=()
    local deployed_json

    if [[ ${#expected_artifacts[@]} -eq 0 ]]; then
        echo "Usage: check_deployments <artifact1> [artifact2] ..." >&2
        return 1
    fi

    # Get deployed artifacts as JSON
    deployed_json=$(claudectl status --format json 2>/dev/null)

    if [[ -z "$deployed_json" ]]; then
        echo "Error: Failed to get deployment status" >&2
        return 1
    fi

    # Check each expected artifact
    for artifact in "${expected_artifacts[@]}"; do
        if ! echo "$deployed_json" | jq -e ".deployments[] | select(.name == \"$artifact\")" >/dev/null 2>&1; then
            missing+=("$artifact")
        fi
    done

    # Report results
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "Error: Missing deployments: ${missing[*]}" >&2
        return 1
    fi

    # Show deployment details
    echo "All expected artifacts are deployed:"
    echo "$deployed_json" | jq -r '.deployments[] | "  \(.name) (\(.type))"'

    return 0
}

# Usage: check_deployments canvas-design pdf-tools code-review

#==============================================================================
# EXAMPLE 3: Sync All Artifacts with Update Check
#==============================================================================
# Check for and apply updates to all artifacts in collection

sync_all() {
    local collection="${1:-default}"
    local updated=0
    local skipped=0

    echo "Syncing all artifacts in collection: $collection"

    # Get list of artifacts
    local artifacts
    artifacts=$(claudectl list --collection "$collection" --format json 2>/dev/null | jq -r '.artifacts[].name')

    if [[ -z "$artifacts" ]]; then
        echo "No artifacts found in collection: $collection" >&2
        return 1
    fi

    # Check and update each artifact
    for artifact in $artifacts; do
        echo "Checking $artifact..."

        # Check for updates (read-only preview)
        local status
        status=$(claudectl sync-check "$artifact" --format json 2>/dev/null)

        if [[ -z "$status" ]]; then
            echo "  Warning: Could not check status" >&2
            ((skipped++))
            continue
        fi

        # Parse JSON to see if updates available
        if echo "$status" | jq -e '.has_updates == true' >/dev/null 2>&1; then
            echo "  Updating $artifact..."
            if claudectl sync-pull "$artifact" --force --format json >/dev/null 2>&1; then
                echo "  ✓ Updated successfully"
                ((updated++))
            else
                echo "  ✗ Update failed" >&2
                ((skipped++))
            fi
        else
            echo "  Already up to date"
        fi
    done

    echo ""
    echo "Summary: $updated updated, $skipped skipped"
    return 0
}

# Usage: sync_all [collection_name]

#==============================================================================
# EXAMPLE 4: Export Collection Backup with Manifest
#==============================================================================
# Create a backup bundle of all artifacts with version information

backup_collection() {
    local collection="${1:-default}"
    local output="${2:-backup-$(date +%Y%m%d).tar.gz}"
    local temp_dir

    if [[ -f "$output" ]]; then
        echo "Error: Output file already exists: $output" >&2
        return 1
    fi

    # Create temporary directory
    temp_dir=$(mktemp -d)
    trap "rm -rf $temp_dir" EXIT

    echo "Creating backup of collection '$collection'..."

    # Get all artifact names and metadata
    local artifacts_json
    artifacts_json=$(claudectl list --collection "$collection" --format json 2>/dev/null)

    if [[ -z "$artifacts_json" ]]; then
        echo "Error: Failed to list artifacts" >&2
        return 1
    fi

    # Check if artifacts exist
    local artifact_count
    artifact_count=$(echo "$artifacts_json" | jq '.artifacts | length')

    if [[ $artifact_count -eq 0 ]]; then
        echo "Error: No artifacts to backup" >&2
        return 1
    fi

    # Save manifest
    echo "$artifacts_json" > "$temp_dir/manifest.json"

    # Export metadata
    echo "Collection: $collection" > "$temp_dir/backup-info.txt"
    echo "Created: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$temp_dir/backup-info.txt"
    echo "Artifacts: $artifact_count" >> "$temp_dir/backup-info.txt"

    # Create bundle
    if ! claudectl bundle create "$output" --collection "$collection" --include-metadata 2>/dev/null; then
        echo "Error: Failed to create bundle" >&2
        return 1
    fi

    echo "Backup created: $output ($(stat -f%z "$output" 2>/dev/null || stat -c%s "$output" 2>/dev/null) bytes)"
    return 0
}

# Usage: backup_collection default backup.tar.gz

#==============================================================================
# EXAMPLE 5: Install from Bundle with Validation
#==============================================================================
# Import and deploy artifacts from a bundle with status verification

install_from_bundle() {
    local bundle_path="$1"
    local project_path="${2:-.}"
    local collection="${3:-imported}"

    if [[ -z "$bundle_path" ]]; then
        echo "Usage: install_from_bundle <bundle_path> [project_path] [collection]" >&2
        return 1
    fi

    if [[ ! -f "$bundle_path" ]]; then
        echo "Error: Bundle not found: $bundle_path" >&2
        return 1
    fi

    if [[ ! -d "$project_path" ]]; then
        echo "Error: Project directory not found: $project_path" >&2
        return 1
    fi

    echo "Importing bundle: $bundle_path"
    echo "  Collection: $collection"
    echo "  Project: $project_path"

    # Import bundle
    if ! claudectl bundle import "$bundle_path" --collection "$collection" --force --format json >/dev/null 2>&1; then
        echo "Error: Failed to import bundle" >&2
        return 1
    fi

    echo "Bundle imported successfully"

    # List imported artifacts
    local artifacts
    artifacts=$(claudectl list --collection "$collection" --format json 2>/dev/null | jq -r '.artifacts[].name')

    if [[ -z "$artifacts" ]]; then
        echo "Warning: No artifacts found in imported collection" >&2
        return 1
    fi

    # Deploy each artifact
    echo ""
    echo "Deploying artifacts..."
    local failed=0

    for artifact in $artifacts; do
        echo "  Deploying $artifact..."
        if ! claudectl deploy "$artifact" --collection "$collection" --project "$project_path" --force >/dev/null 2>&1; then
            echo "    ✗ Failed" >&2
            ((failed++))
        else
            echo "    ✓ Success"
        fi
    done

    echo ""
    if [[ $failed -eq 0 ]]; then
        echo "Installation complete: All artifacts deployed"
        return 0
    else
        echo "Installation complete: $failed artifact(s) failed to deploy" >&2
        return 1
    fi
}

# Usage: install_from_bundle backup.tar.gz /path/to/project

#==============================================================================
# EXAMPLE 6: CI/CD Pipeline Integration
#==============================================================================
# Example for GitHub Actions or GitLab CI integration

ci_pipeline_example() {
    local target_project="${1:-.}"

    echo "=== SkillMeat CI/CD Pipeline Setup ==="

    # Ensure claudectl is available
    if ! command -v claudectl &>/dev/null; then
        echo "Installing SkillMeat..."
        if ! pip install skillmeat >/dev/null 2>&1; then
            echo "Error: Failed to install skillmeat" >&2
            return 1
        fi

        echo "Setting up claudectl alias..."
        if ! skillmeat alias install --force >/dev/null 2>&1; then
            echo "Error: Failed to set up alias" >&2
            return 1
        fi

        export PATH="$HOME/.local/bin:$PATH"
    fi

    # Verify installation
    echo ""
    echo "Verifying installation..."
    claudectl --version || return 1

    # Deploy required artifacts
    local required_artifacts=(
        "anthropics/skills/code-review"
        "anthropics/skills/testing"
        "anthropics/skills/documentation"
    )

    echo ""
    echo "Setting up required artifacts..."

    for spec in "${required_artifacts[@]}"; do
        local artifact_name
        artifact_name=$(basename "$spec")

        echo "  Checking $artifact_name..."

        # Check if artifact exists in collection
        if ! claudectl show "$artifact_name" --format json >/dev/null 2>&1; then
            echo "    Adding $artifact_name..."
            if ! claudectl quick-add "$spec" --force >/dev/null 2>&1; then
                echo "    Warning: Could not add $artifact_name" >&2
                continue
            fi
        fi

        # Deploy to project
        echo "    Deploying to $target_project..."
        if ! claudectl deploy "$artifact_name" --project "$target_project" --force >/dev/null 2>&1; then
            echo "    Warning: Could not deploy $artifact_name" >&2
            continue
        fi
        echo "    ✓ Deployed"
    done

    # Verify deployments
    echo ""
    echo "Verifying deployments..."
    claudectl status --format json

    return 0
}

# Usage: ci_pipeline_example /path/to/project

#==============================================================================
# EXAMPLE 7: Error Handling with Exit Codes and Retry Logic
#==============================================================================
# Proper error handling based on exit codes with automatic retries

deploy_with_retry() {
    local artifact="$1"
    local project="${2:-.}"
    local max_retries=3
    local retry_count=0

    if [[ -z "$artifact" ]]; then
        echo "Usage: deploy_with_retry <artifact> [project]" >&2
        return 2
    fi

    while [[ $retry_count -lt $max_retries ]]; do
        echo "Deploying $artifact (attempt $((retry_count + 1))/$max_retries)..."

        claudectl deploy "$artifact" --project "$project" --force --format json >/dev/null 2>&1
        local exit_code=$?

        case $exit_code in
            0)
                echo "Success"
                return 0
                ;;
            1)
                echo "Error: General failure" >&2
                ((retry_count++))
                if [[ $retry_count -lt $max_retries ]]; then
                    echo "  Retrying in 2 seconds..."
                    sleep 2
                fi
                ;;
            2)
                echo "Error: Invalid usage" >&2
                return 2
                ;;
            3)
                echo "Error: Artifact not found" >&2
                echo "  Searching for similar artifacts..."
                claudectl search "$artifact" --limit 3
                return 3
                ;;
            4)
                echo "Error: Conflict (already deployed?)" >&2
                return 4
                ;;
            5)
                echo "Error: Permission denied" >&2
                return 5
                ;;
            *)
                echo "Error: Unknown exit code $exit_code" >&2
                ((retry_count++))
                if [[ $retry_count -lt $max_retries ]]; then
                    echo "  Retrying in 2 seconds..."
                    sleep 2
                fi
                ;;
        esac
    done

    echo "Error: Failed after $max_retries attempts" >&2
    return 1
}

# Usage: deploy_with_retry my-skill /path/to/project

#==============================================================================
# EXAMPLE 8: Batch Deployment with JSON Reporting
#==============================================================================
# Deploy multiple artifacts with detailed JSON status reporting

batch_deploy() {
    local project="$1"
    shift
    local artifacts=("$@")
    local results_json="batch-deploy-$(date +%s).json"
    local deployed=0
    local failed=0

    if [[ -z "$project" ]] || [[ ${#artifacts[@]} -eq 0 ]]; then
        echo "Usage: batch_deploy <project> <artifact1> [artifact2] ..." >&2
        return 1
    fi

    if [[ ! -d "$project" ]]; then
        echo "Error: Project directory not found: $project" >&2
        return 1
    fi

    echo "Batch deploying ${#artifacts[@]} artifacts to $project..."
    echo "Results will be saved to: $results_json"

    # Initialize results array
    local results="[]"

    # Deploy each artifact
    for artifact in "${artifacts[@]}"; do
        echo "  Deploying $artifact..."

        local start_time
        start_time=$(date +%s)

        # Deploy and capture output
        local deploy_output
        deploy_output=$(claudectl deploy "$artifact" --project "$project" --force --format json 2>&1)
        local exit_code=$?

        local end_time
        end_time=$(date +%s)
        local duration=$((end_time - start_time))

        # Build result object
        local status="failed"
        local error_msg=""

        if [[ $exit_code -eq 0 ]]; then
            status="success"
            ((deployed++))
        else
            error_msg=$(echo "$deploy_output" | head -1)
            ((failed++))
        fi

        # Add to results array using jq
        results=$(echo "$results" | jq \
            --arg name "$artifact" \
            --arg status "$status" \
            --arg error "$error_msg" \
            --arg duration "$duration" \
            '. += [{name: $name, status: $status, error: $error, duration_seconds: $duration}]')
    done

    # Save results
    echo "$results" | jq '.' > "$results_json"

    # Print summary
    echo ""
    echo "Deployment Summary:"
    echo "  Successful: $deployed"
    echo "  Failed: $failed"
    echo "  Total: ${#artifacts[@]}"
    echo ""
    echo "Results saved to: $results_json"

    # Print failed artifacts if any
    if [[ $failed -gt 0 ]]; then
        echo ""
        echo "Failed deployments:"
        echo "$results" | jq '.[] | select(.status == "failed") | "  \(.name): \(.error)"' -r
        return 1
    fi

    return 0
}

# Usage: batch_deploy /path/to/project canvas-design pdf-tools code-review

#==============================================================================
# EXAMPLE 9: Collection Audit Report
#==============================================================================
# Generate detailed audit report of collection state with JSON export

audit_collection() {
    local collection="${1:-default}"
    local output_dir="${2:-.}"
    local report_file="$output_dir/audit-${collection}-$(date +%Y%m%d-%H%M%S).json"

    echo "Auditing collection: $collection"

    # Get collection data
    local collection_data
    collection_data=$(claudectl list --collection "$collection" --format json 2>/dev/null)

    if [[ -z "$collection_data" ]]; then
        echo "Error: Failed to get collection data" >&2
        return 1
    fi

    # Create audit report
    local audit_report
    audit_report=$(jq \
        --arg collection "$collection" \
        --arg timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        '{
            audit: {
                collection: $collection,
                timestamp: $timestamp
            },
            statistics: {
                total_artifacts: (.artifacts | length),
                by_type: (.artifacts | group_by(.type) | map({type: .[0].type, count: length}) | from_entries)
            },
            artifacts: .artifacts
        }' <<< "$collection_data")

    # Add deployment information
    local deployment_status
    deployment_status=$(claudectl status --format json 2>/dev/null)

    if [[ -n "$deployment_status" ]]; then
        audit_report=$(echo "$audit_report" | jq \
            --argjson deployments "$deployment_status" \
            '. + {deployments: $deployments}')
    fi

    # Save report
    echo "$audit_report" | jq '.' > "$report_file"

    # Print summary
    echo ""
    echo "Audit Report:"
    echo "$audit_report" | jq -r '
        "  Collection: \(.audit.collection)",
        "  Timestamp: \(.audit.timestamp)",
        "  Total Artifacts: \(.statistics.total_artifacts)",
        "  By Type: " + (.statistics.by_type | to_entries | map("    \(.key): \(.value)") | join("\n"))
    '

    echo ""
    echo "Full report saved to: $report_file"
    return 0
}

# Usage: audit_collection default .

#==============================================================================
# UTILITY FUNCTIONS
#==============================================================================

# Check if claudectl is installed and working
check_claudectl() {
    if ! command -v claudectl &>/dev/null; then
        echo "Error: claudectl not found in PATH" >&2
        echo "Install SkillMeat and set up the alias:" >&2
        echo "  pip install skillmeat" >&2
        echo "  skillmeat alias install" >&2
        return 1
    fi

    # Test claudectl is functional
    if ! claudectl --version >/dev/null 2>&1; then
        echo "Error: claudectl is not functional" >&2
        return 1
    fi

    return 0
}

# Pretty print JSON with error handling
pretty_json() {
    local json_input
    read -r json_input

    if command -v jq &>/dev/null; then
        echo "$json_input" | jq '.'
    else
        echo "$json_input"
    fi
}

#==============================================================================
# MAIN
#==============================================================================
# Display usage information if script is executed directly

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "claudectl Scripting Examples"
    echo "============================"
    echo ""
    echo "This file contains example functions for automating SkillMeat operations."
    echo "Source it in your scripts to use:"
    echo ""
    echo "  source docs/claudectl-examples.sh"
    echo ""
    echo "Available functions:"
    echo ""
    echo "Deployment:"
    echo "  deploy_bundle <project_path>"
    echo "  deploy_with_retry <artifact> [project]"
    echo "  batch_deploy <project> <artifact1> [artifact2] ..."
    echo ""
    echo "Status & Verification:"
    echo "  check_deployments <artifact1> [artifact2] ..."
    echo "  check_claudectl"
    echo ""
    echo "Collection Management:"
    echo "  sync_all [collection]"
    echo "  backup_collection [collection] [output_file]"
    echo "  install_from_bundle <bundle_path> [project_path] [collection]"
    echo "  audit_collection [collection] [output_dir]"
    echo ""
    echo "CI/CD Integration:"
    echo "  ci_pipeline_example [project]"
    echo ""
    echo "Utilities:"
    echo "  pretty_json (for piping JSON output)"
    echo ""
    echo "Example Usage:"
    echo "  source docs/claudectl-examples.sh"
    echo "  check_claudectl"
    echo "  deploy_bundle /path/to/project"
    echo "  batch_deploy /path/to/project canvas-design pdf-tools"
    echo ""
fi
