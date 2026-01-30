#!/usr/bin/env node
/**
 * check-screenshots.js - Screenshot validator
 *
 * Reads screenshots.json and validates that each referenced screenshot file
 * exists in the docs/screenshots/ directory. Reports missing screenshots
 * and exit with error code if any required screenshots are missing.
 *
 * Usage: node check-screenshots.js [options]
 *
 * Options:
 *   --category <cat>   Check only specific category (readme, features, cli, gifs)
 *   --required-only    Only check screenshots with status != 'pending'
 *   --verbose          Show all screenshots, not just missing ones
 *   --help             Show help message
 *
 * Exit codes:
 *   0 - All required screenshots exist
 *   1 - Missing screenshots found or error
 *
 * @example
 *   node check-screenshots.js                     # Check all screenshots
 *   node check-screenshots.js --category readme   # Check README screenshots only
 *   node check-screenshots.js --required-only     # Skip pending screenshots
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
    category: null,
    requiredOnly: false,
    verbose: false,
    help: false
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--category':
        options.category = args[++i];
        break;
      case '--required-only':
        options.requiredOnly = true;
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
check-screenshots.js - Validate screenshot files exist

Usage: node check-screenshots.js [options]

Options:
  --category <cat>   Check only specific category (readme, features, cli, gifs)
  --required-only    Only check screenshots with status != 'pending'
  --verbose, -v      Show all screenshots, not just missing ones
  --help, -h         Show this help message

Exit Codes:
  0 - All required screenshots exist
  1 - Missing screenshots found or error

Categories:
  readme    - Screenshots used in README.md
  features  - Feature documentation screenshots
  cli       - CLI output screenshots
  gifs      - Animated GIF recordings

Examples:
  node check-screenshots.js                     # Check all screenshots
  node check-screenshots.js --category readme   # Check README screenshots only
  node check-screenshots.js --required-only     # Skip pending screenshots
  node check-screenshots.js --verbose           # Show status of all files
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
 * Check if a file exists
 * @param {string} filepath - Path to check
 * @returns {Object} Result with exists flag and file info
 */
function checkFileExists(filepath) {
  try {
    const stats = fs.statSync(filepath);
    return {
      exists: true,
      size: stats.size,
      modified: stats.mtime
    };
  } catch (err) {
    return {
      exists: false,
      error: err.code
    };
  }
}

/**
 * Format file size for display
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size
 */
function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Validate screenshots from screenshots.json
 * @param {Object} data - Screenshots data
 * @param {Object} options - Validation options
 * @returns {Object} Validation results
 */
function validateScreenshots(data, options) {
  const results = {
    total: 0,
    checked: 0,
    found: 0,
    missing: [],
    skipped: 0,
    byCategory: {},
    byStatus: {}
  };

  // Process static screenshots
  const screenshots = data.screenshots || [];

  for (const screenshot of screenshots) {
    results.total++;

    // Initialize category tracking
    if (!results.byCategory[screenshot.category]) {
      results.byCategory[screenshot.category] = { total: 0, found: 0, missing: 0 };
    }
    results.byCategory[screenshot.category].total++;

    // Initialize status tracking
    const status = screenshot.status || 'unknown';
    if (!results.byStatus[status]) {
      results.byStatus[status] = 0;
    }
    results.byStatus[status]++;

    // Filter by category if specified
    if (options.category && screenshot.category !== options.category) {
      results.skipped++;
      continue;
    }

    // Skip pending if --required-only
    if (options.requiredOnly && screenshot.status === 'pending') {
      results.skipped++;
      if (options.verbose) {
        console.log(`  [SKIP] ${screenshot.file} (pending)`);
      }
      continue;
    }

    results.checked++;

    // Check if file exists
    const filepath = path.join(PROJECT_ROOT, screenshot.file);
    const fileCheck = checkFileExists(filepath);

    if (fileCheck.exists) {
      results.found++;
      results.byCategory[screenshot.category].found++;

      if (options.verbose) {
        console.log(`  [OK] ${screenshot.file} (${formatSize(fileCheck.size)})`);
      }
    } else {
      results.missing.push({
        id: screenshot.id,
        file: screenshot.file,
        category: screenshot.category,
        status: screenshot.status,
        alt: screenshot.alt,
        notes: screenshot.notes,
        resolvedPath: filepath
      });
      results.byCategory[screenshot.category].missing++;

      console.log(`  [MISSING] ${screenshot.file}`);
      if (options.verbose) {
        console.log(`            ID: ${screenshot.id}`);
        console.log(`            Category: ${screenshot.category}`);
        if (screenshot.notes) {
          console.log(`            Notes: ${screenshot.notes}`);
        }
      }
    }
  }

  return results;
}

/**
 * Validate GIF recordings from screenshots.json
 * @param {Object} data - Screenshots data
 * @param {Object} options - Validation options
 * @returns {Object} Validation results for GIFs
 */
function validateGifs(data, options) {
  const results = {
    total: 0,
    checked: 0,
    found: 0,
    missing: [],
    skipped: 0
  };

  const gifs = data.gifs || [];

  for (const gif of gifs) {
    results.total++;

    // Filter by category if gifs category requested
    if (options.category && options.category !== 'gifs') {
      results.skipped++;
      continue;
    }

    // Skip pending if --required-only
    if (options.requiredOnly && gif.status === 'pending') {
      results.skipped++;
      if (options.verbose) {
        console.log(`  [SKIP] ${gif.file} (pending GIF)`);
      }
      continue;
    }

    results.checked++;

    // Check if file exists
    const filepath = path.join(PROJECT_ROOT, gif.file);
    const fileCheck = checkFileExists(filepath);

    if (fileCheck.exists) {
      results.found++;
      if (options.verbose) {
        console.log(`  [OK] ${gif.file} (${formatSize(fileCheck.size)})`);
      }
    } else {
      results.missing.push({
        id: gif.id,
        file: gif.file,
        category: 'gifs',
        status: gif.status,
        alt: gif.alt,
        tool: gif.tool,
        sequence: gif.sequence,
        resolvedPath: filepath
      });

      console.log(`  [MISSING] ${gif.file}`);
      if (options.verbose) {
        console.log(`            ID: ${gif.id}`);
        console.log(`            Tool: ${gif.tool}`);
        if (gif.sequence) {
          console.log(`            Steps: ${gif.sequence.length}`);
        }
      }
    }
  }

  return results;
}

/**
 * Print validation summary
 * @param {Object} screenshotResults - Screenshot validation results
 * @param {Object} gifResults - GIF validation results
 * @param {Object} options - Print options
 */
function printSummary(screenshotResults, gifResults, options) {
  console.log('\n--- Summary ---\n');

  // Screenshot summary
  console.log('Screenshots:');
  console.log(`  Total:    ${screenshotResults.total}`);
  console.log(`  Checked:  ${screenshotResults.checked}`);
  console.log(`  Found:    ${screenshotResults.found}`);
  console.log(`  Missing:  ${screenshotResults.missing.length}`);
  console.log(`  Skipped:  ${screenshotResults.skipped}`);

  // By category breakdown
  if (options.verbose && Object.keys(screenshotResults.byCategory).length > 0) {
    console.log('\n  By Category:');
    for (const [cat, stats] of Object.entries(screenshotResults.byCategory)) {
      console.log(`    ${cat}: ${stats.found}/${stats.total} found`);
    }
  }

  // By status breakdown
  if (options.verbose && Object.keys(screenshotResults.byStatus).length > 0) {
    console.log('\n  By Status:');
    for (const [status, count] of Object.entries(screenshotResults.byStatus)) {
      console.log(`    ${status}: ${count}`);
    }
  }

  // GIF summary
  if (gifResults.total > 0) {
    console.log('\nGIFs:');
    console.log(`  Total:    ${gifResults.total}`);
    console.log(`  Checked:  ${gifResults.checked}`);
    console.log(`  Found:    ${gifResults.found}`);
    console.log(`  Missing:  ${gifResults.missing.length}`);
    console.log(`  Skipped:  ${gifResults.skipped}`);
  }

  // Combined missing files
  const totalMissing = screenshotResults.missing.length + gifResults.missing.length;

  if (totalMissing > 0) {
    console.log('\n--- Missing Files ---\n');

    for (const item of [...screenshotResults.missing, ...gifResults.missing]) {
      console.log(`  ${item.file}`);
      console.log(`    ID: ${item.id}`);
      console.log(`    Category: ${item.category}`);
      console.log(`    Status: ${item.status}`);
      if (item.notes) {
        console.log(`    Notes: ${item.notes}`);
      }
      console.log('');
    }

    // Helpful hint for capturing
    console.log('To capture missing screenshots:');
    console.log('  1. Start the web server: skillmeat web dev');
    console.log('  2. Navigate to the target page');
    console.log('  3. Capture using browser devtools or Claude in Chrome');
    console.log('  4. Save to the correct path in docs/screenshots/');
    console.log('  5. Update status in screenshots.json to "captured"');
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

  console.log('Checking screenshots...\n');

  // Load screenshots data
  const screenshotsPath = path.join(DATA_DIR, 'screenshots.json');
  const data = loadJson(screenshotsPath);

  if (!data) {
    process.exit(1);
  }

  console.log(`  File: ${screenshotsPath}`);
  console.log(`  Version: ${data.version || 'not set'}`);
  console.log(`  Screenshots: ${data.screenshots?.length || 0}`);
  console.log(`  GIFs: ${data.gifs?.length || 0}`);

  if (options.category) {
    console.log(`  Filter: ${options.category}`);
  }
  if (options.requiredOnly) {
    console.log(`  Mode: required-only (skipping pending)`);
  }
  console.log('');

  // Validate screenshots
  const screenshotResults = validateScreenshots(data, options);

  // Validate GIFs
  const gifResults = validateGifs(data, options);

  // Print summary
  printSummary(screenshotResults, gifResults, options);

  // Determine exit code
  const totalMissing = screenshotResults.missing.length + gifResults.missing.length;

  if (totalMissing > 0) {
    // In required-only mode, only fail if non-pending screenshots are missing
    if (options.requiredOnly) {
      console.log(`\nValidation FAILED: ${totalMissing} required screenshot(s) missing.`);
    } else {
      console.log(`\nValidation FAILED: ${totalMissing} screenshot(s) missing.`);
      console.log('Tip: Use --required-only to skip pending screenshots.');
    }
    process.exit(1);
  } else {
    console.log('\nValidation PASSED: All checked screenshots exist.');
    process.exit(0);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

// Export for testing
module.exports = {
  checkFileExists,
  validateScreenshots,
  validateGifs,
  formatSize,
  parseArgs
};
