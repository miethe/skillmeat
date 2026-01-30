#!/usr/bin/env node
/**
 * sync-features.js - Feature sync and validation
 *
 * Validates features.json schema and structure. Can be extended to sync
 * feature definitions from code annotations or external sources.
 *
 * Usage: node sync-features.js [options]
 *
 * Options:
 *   --validate        Validate schema only (default behavior)
 *   --check-refs      Check that referenced screenshots exist
 *   --check-pages     Check that webPage paths are valid
 *   --verbose         Show detailed validation output
 *   --help            Show help message
 *
 * Exit codes:
 *   0 - Validation passed
 *   1 - Validation errors found
 *
 * @example
 *   node sync-features.js                 # Basic validation
 *   node sync-features.js --check-refs    # Also check screenshot references
 *   node sync-features.js --verbose       # Detailed output
 */

const fs = require('fs');
const path = require('path');

// Script directory for relative paths
const SCRIPT_DIR = __dirname;
const DATA_DIR = path.join(SCRIPT_DIR, '..', 'data');
const PROJECT_ROOT = path.join(SCRIPT_DIR, '..', '..', '..');

/**
 * Parse command line arguments
 * @returns {Object} Parsed arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    validate: true,
    checkRefs: false,
    checkPages: false,
    verbose: false,
    help: false
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--validate':
        options.validate = true;
        break;
      case '--check-refs':
        options.checkRefs = true;
        break;
      case '--check-pages':
        options.checkPages = true;
        break;
      case '--verbose':
      case '-v':
        options.verbose = true;
        break;
      case '--help':
      case '-h':
        options.help = true;
        break;
      default:
        if (args[i].startsWith('-')) {
          console.error(`Unknown option: ${args[i]}`);
          process.exit(1);
        }
    }
  }

  return options;
}

/**
 * Display help message
 */
function showHelp() {
  console.log(`
sync-features.js - Feature validation and sync

Usage: node sync-features.js [options]

Options:
  --validate        Validate schema only (default behavior)
  --check-refs      Check that referenced screenshots exist in screenshots.json
  --check-pages     Check that webPage paths correspond to valid routes
  --verbose, -v     Show detailed validation output
  --help, -h        Show this help message

Exit Codes:
  0 - Validation passed
  1 - Validation errors found

Examples:
  node sync-features.js                 # Basic validation
  node sync-features.js --check-refs    # Also check screenshot references
  node sync-features.js --verbose       # Detailed output

Schema Validation Checks:
  - Required fields: id, name, description
  - Valid version format for 'since' field
  - No duplicate feature IDs
  - Category structure validity
`);
}

/**
 * Load JSON file with error handling
 * @param {string} filepath - Path to JSON file
 * @returns {Object|null} Parsed JSON or null on error
 */
function loadJson(filepath) {
  try {
    const content = fs.readFileSync(filepath, 'utf8');
    return JSON.parse(content);
  } catch (err) {
    if (err.code === 'ENOENT') {
      console.error(`File not found: ${filepath}`);
    } else if (err instanceof SyntaxError) {
      console.error(`Invalid JSON in ${filepath}: ${err.message}`);
    } else {
      console.error(`Error loading ${filepath}: ${err.message}`);
    }
    return null;
  }
}

/**
 * Validate version format (semver-like)
 * @param {string} version - Version string
 * @returns {boolean} True if valid
 */
function isValidVersion(version) {
  const semverPattern = /^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$/;
  return semverPattern.test(version);
}

/**
 * Validate a single feature object
 * @param {Object} feature - Feature object
 * @param {string} categoryId - Parent category ID
 * @returns {Array<string>} Array of error messages
 */
function validateFeature(feature, categoryId) {
  const errors = [];
  const prefix = `Feature "${feature.id || 'unknown'}" in category "${categoryId}"`;

  // Required fields
  if (!feature.id) {
    errors.push(`${prefix}: missing required field 'id'`);
  } else if (typeof feature.id !== 'string') {
    errors.push(`${prefix}: 'id' must be a string`);
  } else if (!/^[a-z0-9-]+$/.test(feature.id)) {
    errors.push(`${prefix}: 'id' should be lowercase alphanumeric with hyphens`);
  }

  if (!feature.name) {
    errors.push(`${prefix}: missing required field 'name'`);
  }

  if (!feature.description) {
    errors.push(`${prefix}: missing required field 'description'`);
  }

  // Optional fields with type validation
  if (feature.since && !isValidVersion(feature.since)) {
    errors.push(`${prefix}: invalid 'since' version format "${feature.since}"`);
  }

  if (feature.cliCommand && typeof feature.cliCommand !== 'string') {
    errors.push(`${prefix}: 'cliCommand' must be a string`);
  }

  if (feature.webPage && typeof feature.webPage !== 'string') {
    errors.push(`${prefix}: 'webPage' must be a string`);
  }

  if (feature.screenshot && typeof feature.screenshot !== 'string') {
    errors.push(`${prefix}: 'screenshot' must be a string`);
  }

  if (feature.highlight !== undefined && typeof feature.highlight !== 'boolean') {
    errors.push(`${prefix}: 'highlight' must be a boolean`);
  }

  if (feature.shortDescription && typeof feature.shortDescription !== 'string') {
    errors.push(`${prefix}: 'shortDescription' must be a string`);
  }

  return errors;
}

/**
 * Validate a category object
 * @param {Object} category - Category object
 * @returns {Array<string>} Array of error messages
 */
function validateCategory(category) {
  const errors = [];
  const prefix = `Category "${category.id || 'unknown'}"`;

  // Required fields
  if (!category.id) {
    errors.push(`${prefix}: missing required field 'id'`);
  }

  if (!category.name) {
    errors.push(`${prefix}: missing required field 'name'`);
  }

  // Features array
  if (!Array.isArray(category.features)) {
    errors.push(`${prefix}: 'features' must be an array`);
  }

  // Optional fields
  if (category.icon && typeof category.icon !== 'string') {
    errors.push(`${prefix}: 'icon' must be a string`);
  }

  if (category.tagline && typeof category.tagline !== 'string') {
    errors.push(`${prefix}: 'tagline' must be a string`);
  }

  return errors;
}

/**
 * Validate the entire features.json structure
 * @param {Object} data - Features data
 * @param {Object} options - Validation options
 * @returns {Object} Validation result with errors and warnings
 */
function validateFeaturesSchema(data, options) {
  const errors = [];
  const warnings = [];
  const featureIds = new Set();

  // Top-level validation
  if (!data.version) {
    errors.push("Missing 'version' field at root level");
  } else if (!isValidVersion(data.version)) {
    errors.push(`Invalid version format: ${data.version}`);
  }

  if (!data.lastUpdated) {
    warnings.push("Missing 'lastUpdated' field at root level");
  }

  if (!Array.isArray(data.categories)) {
    errors.push("'categories' must be an array");
    return { errors, warnings };
  }

  // Validate each category
  for (const category of data.categories) {
    errors.push(...validateCategory(category));

    if (!Array.isArray(category.features)) continue;

    // Validate features in category
    for (const feature of category.features) {
      errors.push(...validateFeature(feature, category.id));

      // Check for duplicate IDs
      if (feature.id) {
        if (featureIds.has(feature.id)) {
          errors.push(`Duplicate feature ID: "${feature.id}"`);
        }
        featureIds.add(feature.id);
      }
    }
  }

  // Validate artifact types if present
  if (data.artifactTypes) {
    if (!Array.isArray(data.artifactTypes)) {
      errors.push("'artifactTypes' must be an array");
    } else {
      const typeIds = new Set();
      for (const type of data.artifactTypes) {
        if (!type.id) {
          errors.push("Artifact type missing 'id' field");
        } else if (typeIds.has(type.id)) {
          errors.push(`Duplicate artifact type ID: "${type.id}"`);
        } else {
          typeIds.add(type.id);
        }
      }
    }
  }

  // Validate stats if present
  if (data.stats) {
    const requiredStats = ['totalCommands', 'commandGroups', 'webPages', 'apiEndpoints'];
    for (const stat of requiredStats) {
      if (data.stats[stat] === undefined) {
        warnings.push(`Missing stat: ${stat}`);
      } else if (typeof data.stats[stat] !== 'number') {
        errors.push(`Stat '${stat}' must be a number`);
      }
    }
  }

  return { errors, warnings, featureCount: featureIds.size };
}

/**
 * Check that screenshot references in features exist in screenshots.json
 * @param {Object} features - Features data
 * @param {Object} screenshots - Screenshots data
 * @returns {Array<string>} Array of error messages
 */
function checkScreenshotReferences(features, screenshots) {
  const errors = [];

  // Build set of valid screenshot files
  const validScreenshots = new Set();
  if (screenshots.screenshots) {
    for (const s of screenshots.screenshots) {
      if (s.file) {
        // Extract filename from path
        const filename = path.basename(s.file);
        validScreenshots.add(filename);
      }
    }
  }

  // Check each feature's screenshot reference
  for (const category of features.categories) {
    if (!Array.isArray(category.features)) continue;

    for (const feature of category.features) {
      if (feature.screenshot && !validScreenshots.has(feature.screenshot)) {
        errors.push(
          `Feature "${feature.id}" references unknown screenshot: ${feature.screenshot}`
        );
      }
    }
  }

  return errors;
}

/**
 * Print validation summary
 * @param {Object} result - Validation result
 * @param {Object} options - Print options
 */
function printSummary(result, options) {
  console.log('\n--- Validation Summary ---\n');

  if (result.featureCount !== undefined) {
    console.log(`  Total features: ${result.featureCount}`);
  }

  console.log(`  Errors: ${result.errors.length}`);
  console.log(`  Warnings: ${result.warnings.length}`);

  if (result.errors.length > 0) {
    console.log('\n--- Errors ---\n');
    for (const error of result.errors) {
      console.log(`  [ERROR] ${error}`);
    }
  }

  if (result.warnings.length > 0 && options.verbose) {
    console.log('\n--- Warnings ---\n');
    for (const warning of result.warnings) {
      console.log(`  [WARN] ${warning}`);
    }
  }
}

/**
 * Main entry point
 */
function main() {
  const options = parseArgs();

  if (options.help) {
    showHelp();
    process.exit(0);
  }

  console.log('Validating features.json...\n');

  // Load features data
  const featuresPath = path.join(DATA_DIR, 'features.json');
  const features = loadJson(featuresPath);

  if (!features) {
    process.exit(1);
  }

  console.log(`  File: ${featuresPath}`);
  console.log(`  Version: ${features.version || 'not set'}`);
  console.log(`  Categories: ${features.categories?.length || 0}`);

  // Validate schema
  const result = validateFeaturesSchema(features, options);

  // Check screenshot references if requested
  if (options.checkRefs) {
    console.log('\nChecking screenshot references...');
    const screenshotsPath = path.join(DATA_DIR, 'screenshots.json');
    const screenshots = loadJson(screenshotsPath);

    if (screenshots) {
      const refErrors = checkScreenshotReferences(features, screenshots);
      result.errors.push(...refErrors);
      console.log(`  Checked ${features.categories?.reduce((sum, c) => sum + (c.features?.filter(f => f.screenshot)?.length || 0), 0) || 0} references`);
    }
  }

  // Check web pages if requested
  if (options.checkPages) {
    console.log('\nNote: --check-pages is a placeholder for future implementation.');
    result.warnings.push('Web page validation not yet implemented');
  }

  // Print summary
  printSummary(result, options);

  // Exit with appropriate code
  if (result.errors.length > 0) {
    console.log(`\nValidation FAILED: ${result.errors.length} error(s) found.`);
    process.exit(1);
  } else {
    console.log('\nValidation PASSED.');
    process.exit(0);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

// Export for testing
module.exports = {
  validateFeature,
  validateCategory,
  validateFeaturesSchema,
  checkScreenshotReferences,
  isValidVersion,
  parseArgs
};
