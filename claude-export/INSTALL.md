# Installation Guide for claude-export

This document explains how to use the `install.sh` script to customize the claude-export configuration system for your project.

## Overview

The `install.sh` script performs template variable substitution, replacing `{{VARIABLE}}` placeholders throughout the claude-export files with actual values from a configuration file.

**Key Features:**
- JSON-based configuration with comprehensive validation
- Dry-run mode to preview changes before applying
- Automatic backup of modified files
- Detailed progress reporting and summary statistics
- Support for custom output directories
- Colorized output for easy readability

## Quick Start

### 1. Basic Installation (In-Place)

```bash
# Install with default config (modifies files in-place)
./install.sh
```

This will:
- Read configuration from `config/template-config.json`
- Find all files with `{{VARIABLE}}` placeholders
- Replace placeholders with values from the config
- Create `.backup` copies of modified files
- Display a summary of changes

### 2. Preview Changes (Dry Run)

```bash
# See what would change without modifying files
./install.sh --dry-run
```

Recommended first step to verify the configuration is correct.

### 3. Custom Configuration

```bash
# Use a custom config file
./install.sh --config=my-project-config.json
```

### 4. Install to Different Directory

```bash
# Output customized files to a different location
./install.sh --output-dir=/path/to/output
```

Useful for:
- Installing to a different project
- Creating multiple configurations
- Testing without modifying the original

### 5. Validate Configuration Only

```bash
# Check if config file is valid without installing
./install.sh --validate --config=my-config.json
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config=FILE` | Path to configuration JSON file | `config/template-config.json` |
| `--output-dir=DIR` | Directory to write customized files | Current directory (in-place) |
| `--dry-run` | Preview changes without modifying files | Disabled |
| `--validate` | Validate config file only | Disabled |
| `--help` | Show usage information | - |

## Configuration File Format

The configuration file is a JSON document with variables organized by category:

```json
{
  "metadata": {
    "projectName": "YourProject",
    "version": "1.0.0",
    "description": "Your project description"
  },
  "identity": {
    "PROJECT_NAME": {
      "description": "Project or organization name",
      "default": "YourProject",
      "required": true,
      "type": "string"
    }
  },
  "architecture": {
    "PROJECT_ARCHITECTURE": {
      "description": "System architecture description",
      "default": "Your architecture description",
      "required": true,
      "type": "string"
    }
  }
  // ... more categories
}
```

**Required Categories:**
- `metadata` - Project metadata
- `identity` - Project identity variables (PROJECT_NAME, etc.)
- `architecture` - Architecture patterns (PROJECT_ARCHITECTURE, LAYER_ARCHITECTURE)
- `standards` - Coding standards (PROJECT_STANDARDS, VALIDATION_RULES)
- `workflow` - PM workflow (PM_WORKFLOW, TASK_TRACKER)

See `config/template-config.json` for the complete structure.

## Variables

The script extracts variables from the configuration file using this pattern:

```json
{
  "category": {
    "VARIABLE_NAME": {
      "default": "The value that will replace {{VARIABLE_NAME}}",
      "description": "What this variable is used for",
      "required": true,
      "type": "string"
    }
  }
}
```

The `default` value is what gets substituted for `{{VARIABLE_NAME}}` in files.

## Files Processed

The script automatically finds and processes files in these directories:

- `agents/` - All `.md` files with variables
- `commands/` - All `.md` files with variables
- `templates/` - All `.md` files with variables
- `config/` - All `.json` files with variables
- `skills/` - All `.md`, `.json`, `.sh` files with variables
- `hooks/` - All shell scripts with variables

Files without any `{{VARIABLE}}` placeholders are skipped.

## Exit Codes

The script uses standard exit codes to indicate status:

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error (missing dependency, invalid argument) |
| 2 | Config file not found or invalid JSON |
| 3 | Missing required variables in config |
| 4 | File processing error |

Use in CI/CD pipelines:

```bash
./install.sh --validate --config=prod-config.json
if [ $? -ne 0 ]; then
  echo "Config validation failed"
  exit 1
fi
```

## Examples

### Example 1: Customizing for a New Project

```bash
# 1. Copy the template config
cp config/template-config.json config/acme-corp-config.json

# 2. Edit the configuration
# Update PROJECT_NAME, PROJECT_ARCHITECTURE, PM_WORKFLOW, etc.

# 3. Validate the config
./install.sh --validate --config=config/acme-corp-config.json

# 4. Preview the changes
./install.sh --dry-run --config=config/acme-corp-config.json

# 5. Apply the changes
./install.sh --config=config/acme-corp-config.json
```

### Example 2: Installing to a Different Directory

```bash
# Install customized version to a project directory
./install.sh \
  --config=config/my-project.json \
  --output-dir=/path/to/my-project/.claude
```

### Example 3: Multiple Project Configurations

```bash
# Create configs for different environments
./install.sh --config=config/dev-config.json --output-dir=./output/dev
./install.sh --config=config/staging-config.json --output-dir=./output/staging
./install.sh --config=config/prod-config.json --output-dir=./output/prod
```

## Output & Reporting

The script provides detailed progress information:

### During Execution

```
========================================
claude-export Template Installation
========================================

Configuration:
  Config file:  config/template-config.json
  Output dir:   /Users/you/claude-export
  Mode:         INSTALL

▸ Checking dependencies...
✓ Dependencies satisfied (jq available)

▸ Validating configuration file: template-config.json
✓ Config file is valid JSON
✓ All required top-level keys present
▸ Checking required variables...
✓ All required variables have values

▸ Extracting variables from config...
✓ Extracted 50+ variables from config

========================================
Processing Files
========================================

▸ Finding templatized files...
✓ Found 150 templatized files

ℹ Processing 150 files...

Processing: agents/pm/implementation-planner.md
Processing: agents/pm/lead-pm.md
Processing: commands/pm/create-adr.md
...
```

### Summary Report

```
========================================
Installation Summary
========================================

Files:
  Total processed:    150
  Modified:           142
  Skipped (no vars):  8
  Backed up:          142

Variables:
  Total replacements: 487
  Unique variables:   53

Most Replaced Variables:
  PROJECT_NAME: 89 times
  PROJECT_ARCHITECTURE: 45 times
  PROJECT_STANDARDS: 38 times
  PM_WORKFLOW: 32 times
  TASK_TRACKER: 28 times
  ...

Modified Files:
  agents/pm/implementation-planner.md
  agents/pm/lead-pm.md
  agents/pm/feature-planner.md
  ...

Installation Complete!
Original files backed up with .backup extension
```

## Backup & Recovery

### Automatic Backups

When running in-place (default mode), the script automatically creates backups:

```bash
# Original file
agents/pm/lead-pm.md

# Backup created automatically
agents/pm/lead-pm.md.backup
```

### Manual Recovery

To restore from backups:

```bash
# Restore a single file
mv agents/pm/lead-pm.md.backup agents/pm/lead-pm.md

# Restore all files
find . -name "*.backup" | while read backup; do
  original="${backup%.backup}"
  mv "$backup" "$original"
done
```

### Remove Backups

After verifying the installation:

```bash
# Remove all backup files
find . -name "*.backup" -delete
```

## Troubleshooting

### Error: "jq is required but not installed"

**Solution:** Install jq:

```bash
# macOS
brew install jq

# Ubuntu/Debian
apt-get install jq

# Fedora/RHEL
yum install jq
```

### Error: "Config file not found"

**Solution:** Check the path to your config file:

```bash
# Verify the file exists
ls -l config/template-config.json

# Use absolute path if needed
./install.sh --config=/full/path/to/config.json
```

### Error: "Invalid JSON in config file"

**Solution:** Validate your JSON syntax:

```bash
# Check JSON syntax with jq
jq . config/template-config.json

# Or use an online validator
# Copy config to https://jsonlint.com/
```

Common JSON errors:
- Missing commas between fields
- Trailing commas in objects/arrays
- Unquoted field names
- Unescaped quotes in strings

### Error: "Missing required variable values"

**Solution:** Ensure all required variables have `default` values:

```json
{
  "identity": {
    "PROJECT_NAME": {
      "default": "",  // ❌ Empty - will fail
      "required": true
    }
  }
}
```

Fix:

```json
{
  "identity": {
    "PROJECT_NAME": {
      "default": "YourProject",  // ✓ Has value
      "required": true
    }
  }
}
```

### Warning: "No value found for variable"

This happens when a file contains `{{VARIABLE_NAME}}` but the variable isn't in the config.

**Solutions:**
1. Add the variable to your config
2. Remove the placeholder from the file
3. Check for typos in variable names

### No files modified in dry-run

This is expected behavior! Dry-run mode shows what *would* change without actually modifying files.

To apply changes, run without `--dry-run`:

```bash
./install.sh  # Applies changes
```

## Advanced Usage

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Validate claude-export config
  run: |
    cd claude-export
    ./install.sh --validate --config=config/prod-config.json

- name: Install claude-export
  run: |
    cd claude-export
    ./install.sh --config=config/prod-config.json --output-dir=../.claude
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Validate claude-export config before commits

if [ -f claude-export/install.sh ]; then
  cd claude-export
  ./install.sh --validate
  if [ $? -ne 0 ]; then
    echo "Error: claude-export config validation failed"
    exit 1
  fi
fi
```

### Variable Override Pattern

You can layer configurations by using multiple config files:

```bash
# Base configuration
./install.sh --config=config/base-config.json --output-dir=./temp

# Override with environment-specific values
cd temp
../install.sh --config=../config/prod-overrides.json
```

## Best Practices

1. **Always run dry-run first:**
   ```bash
   ./install.sh --dry-run --config=my-config.json
   ```

2. **Validate before installing:**
   ```bash
   ./install.sh --validate --config=my-config.json
   ```

3. **Keep configs in version control:**
   ```bash
   git add config/my-project-config.json
   git commit -m "Add project configuration"
   ```

4. **Test in a separate directory first:**
   ```bash
   ./install.sh --config=my-config.json --output-dir=./test-output
   # Verify ./test-output looks correct
   # Then apply in-place
   ./install.sh --config=my-config.json
   ```

5. **Document custom variables:**
   Add comments to your config explaining project-specific choices:
   ```json
   {
     "identity": {
       "PROJECT_NAME": {
         "default": "Acme Corp",
         "description": "Using Acme Corp as it's our legal entity name",
         "required": true
       }
     }
   }
   ```

## Related Documentation

- **[TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md)** - Complete guide to all 50+ variables
- **[config/template-config.json](./config/template-config.json)** - Full template configuration
- **[CLAUDE.md](./CLAUDE.md)** - Operating manual for claude-export
- **[README.md](./README.md)** - Project overview

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Validate your config: `./install.sh --validate`
3. Run in dry-run mode to see what would change: `./install.sh --dry-run`
4. Review the TEMPLATIZATION_GUIDE.md for variable documentation
5. Check the exit code for specific error types

## Version History

- **2025-11-05** - Initial release
  - Full variable substitution support
  - 50+ configurable variables
  - Dry-run and validation modes
  - Automatic backup creation
  - Detailed summary reporting
