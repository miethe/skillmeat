#!/usr/bin/env node
/**
 * update-version.js - Version updater for README system
 *
 * Updates version references in version.json and timestamps in features.json
 * and screenshots.json. Maintains version history for release tracking.
 *
 * Usage: node update-version.js [options]
 *
 * Options:
 *   --version <ver>       Set new version (e.g., 0.4.0, 0.4.0-beta)
 *   --release-date <date> Set release date (YYYY-MM-DD format)
 *   --dry-run             Preview changes without writing
 *   --help                Show help message
 *
 * @example
 *   node update-version.js --version 0.4.0
 *   node update-version.js --version 0.4.0 --release-date 2026-02-15
 *   node update-version.js --version 0.4.0-beta --dry-run
 */

const fs = require('fs');
const path = require('path');

// Script directory for relative paths
const SCRIPT_DIR = __dirname;
const DATA_DIR = path.join(SCRIPT_DIR, '..', 'data');

/**
 * Parse command line arguments
 * @returns {Object} Parsed arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    version: null,
    releaseDate: null,
    dryRun: false,
    help: false
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--version':
        options.version = args[++i];
        break;
      case '--release-date':
        options.releaseDate = args[++i];
        break;
      case '--dry-run':
        options.dryRun = true;
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
update-version.js - Update version references in README data files

Usage: node update-version.js [options]

Options:
  --version <ver>       Set new version (e.g., 0.4.0, 0.4.0-beta)
  --release-date <date> Set release date (YYYY-MM-DD format)
  --dry-run             Preview changes without writing files
  --help, -h            Show this help message

Examples:
  node update-version.js --version 0.4.0
  node update-version.js --version 0.4.0 --release-date 2026-02-15
  node update-version.js --version 0.4.0-beta --dry-run

Notes:
  - If release-date is not provided, today's date is used
  - Version format should follow semver (e.g., 0.4.0, 0.4.0-beta, 0.4.0-alpha.1)
  - Previous version is automatically archived in version history
`);
}

/**
 * Validate version string format
 * @param {string} version - Version string to validate
 * @returns {boolean} True if valid
 */
function isValidVersion(version) {
  // Basic semver pattern with optional pre-release suffix
  const semverPattern = /^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$/;
  return semverPattern.test(version);
}

/**
 * Validate date string format
 * @param {string} date - Date string to validate
 * @returns {boolean} True if valid
 */
function isValidDate(date) {
  const datePattern = /^\d{4}-\d{2}-\d{2}$/;
  if (!datePattern.test(date)) return false;

  // Check if it's a valid date
  const parsed = new Date(date);
  return !isNaN(parsed.getTime());
}

/**
 * Load JSON file with error handling
 * @param {string} filepath - Path to JSON file
 * @returns {Object} Parsed JSON data
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
    process.exit(1);
  }
}

/**
 * Write JSON file with formatting
 * @param {string} filepath - Path to JSON file
 * @param {Object} data - Data to write
 * @param {boolean} dryRun - If true, log instead of writing
 */
function writeJson(filepath, data, dryRun) {
  const content = JSON.stringify(data, null, 2) + '\n';

  if (dryRun) {
    const filename = path.basename(filepath);
    console.log(`\n--- ${filename} (DRY RUN) ---`);
    console.log(content.slice(0, 500) + (content.length > 500 ? '\n...(truncated)' : ''));
    return;
  }

  try {
    fs.writeFileSync(filepath, content, 'utf8');
    console.log(`  Updated: ${filepath}`);
  } catch (err) {
    console.error(`Error writing ${filepath}: ${err.message}`);
    process.exit(1);
  }
}

/**
 * Update version.json with new version
 * @param {string} newVersion - New version string
 * @param {string} releaseDate - Release date (YYYY-MM-DD)
 * @param {boolean} dryRun - If true, preview only
 * @returns {Object} Updated version data
 */
function updateVersionFile(newVersion, releaseDate, dryRun) {
  const filepath = path.join(DATA_DIR, 'version.json');
  const data = loadJson(filepath);

  // Archive current version if different
  if (data.current && data.current !== newVersion) {
    // Create history entry for current version
    const historyEntry = {
      version: data.current,
      releaseDate: data.releaseDate,
      highlights: [] // Could be populated from changelog
    };

    // Add to previousVersions array
    if (!Array.isArray(data.previousVersions)) {
      data.previousVersions = [];
    }

    // Avoid duplicates
    const exists = data.previousVersions.some(v => v.version === data.current);
    if (!exists) {
      data.previousVersions.unshift(historyEntry);
    }

    console.log(`  Archived version ${data.current} to history`);
  }

  // Update current version
  data.current = newVersion;
  data.releaseDate = releaseDate;

  // Update upcoming if it matches new version
  if (data.upcoming && data.upcoming.version === newVersion) {
    data.upcoming = {
      version: incrementVersion(newVersion),
      plannedFeatures: []
    };
  }

  writeJson(filepath, data, dryRun);
  return data;
}

/**
 * Update lastUpdated timestamp in features.json
 * @param {string} date - Date string (YYYY-MM-DD)
 * @param {string} version - Version string to update
 * @param {boolean} dryRun - If true, preview only
 */
function updateFeaturesFile(date, version, dryRun) {
  const filepath = path.join(DATA_DIR, 'features.json');
  const data = loadJson(filepath);

  data.lastUpdated = date;
  data.version = version;

  writeJson(filepath, data, dryRun);
}

/**
 * Update lastUpdated timestamp in screenshots.json
 * @param {string} date - Date string (YYYY-MM-DD)
 * @param {string} version - Version string to update
 * @param {boolean} dryRun - If true, preview only
 */
function updateScreenshotsFile(date, version, dryRun) {
  const filepath = path.join(DATA_DIR, 'screenshots.json');
  const data = loadJson(filepath);

  data.lastUpdated = date;
  data.version = version;

  writeJson(filepath, data, dryRun);
}

/**
 * Increment version number (simple patch bump)
 * @param {string} version - Current version
 * @returns {string} Incremented version
 */
function incrementVersion(version) {
  // Strip pre-release suffix for increment
  const base = version.replace(/-.*$/, '');
  const parts = base.split('.');

  if (parts.length >= 3) {
    parts[2] = String(parseInt(parts[2], 10) + 1);
  }

  return parts.join('.');
}

/**
 * Get today's date in YYYY-MM-DD format
 * @returns {string} Today's date
 */
function getTodayDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
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

  // Validate required arguments
  if (!options.version) {
    console.error('Error: --version is required');
    console.error('Run with --help for usage information');
    process.exit(1);
  }

  if (!isValidVersion(options.version)) {
    console.error(`Error: Invalid version format: ${options.version}`);
    console.error('Version should follow semver (e.g., 0.4.0, 0.4.0-beta)');
    process.exit(1);
  }

  // Use provided date or today
  const releaseDate = options.releaseDate || getTodayDate();

  if (options.releaseDate && !isValidDate(options.releaseDate)) {
    console.error(`Error: Invalid date format: ${options.releaseDate}`);
    console.error('Date should be in YYYY-MM-DD format');
    process.exit(1);
  }

  console.log('Updating version references...\n');
  console.log(`  New version: ${options.version}`);
  console.log(`  Release date: ${releaseDate}`);

  if (options.dryRun) {
    console.log('  Mode: DRY RUN (no files will be modified)\n');
  } else {
    console.log('');
  }

  // Update all files
  updateVersionFile(options.version, releaseDate, options.dryRun);
  updateFeaturesFile(releaseDate, options.version, options.dryRun);
  updateScreenshotsFile(releaseDate, options.version, options.dryRun);

  console.log('\nVersion update complete!');

  if (!options.dryRun) {
    console.log('\nNext steps:');
    console.log('  1. Run: node build-readme.js');
    console.log('  2. Review changes: git diff');
    console.log('  3. Commit: git commit -am "chore: bump version to ' + options.version + '"');
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

// Export for testing
module.exports = {
  isValidVersion,
  isValidDate,
  incrementVersion,
  parseArgs
};
