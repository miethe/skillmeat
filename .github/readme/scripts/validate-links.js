#!/usr/bin/env node
/**
 * validate-links.js - Link checker for README.md
 *
 * Reads README.md from project root and validates all markdown links.
 * Checks internal file references exist and reports broken links.
 *
 * Usage: node validate-links.js [options]
 *
 * Options:
 *   --file <path>     Path to README file (default: project root README.md)
 *   --check-external  Also validate external URLs (slower)
 *   --verbose         Show all links, not just broken ones
 *   --help            Show help message
 *
 * Exit codes:
 *   0 - All links valid
 *   1 - Broken links found or error
 *
 * @example
 *   node validate-links.js                    # Check project README
 *   node validate-links.js --verbose          # Show all links
 *   node validate-links.js --check-external   # Also check URLs
 */

const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

// Script directory for relative paths
const SCRIPT_DIR = __dirname;
const PROJECT_ROOT = path.join(SCRIPT_DIR, '..', '..', '..');

/**
 * Parse command line arguments
 * @returns {Object} Parsed arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    file: null,
    checkExternal: false,
    verbose: false,
    help: false
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--file':
        options.file = args[++i];
        break;
      case '--check-external':
        options.checkExternal = true;
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
validate-links.js - Validate links in README.md

Usage: node validate-links.js [options]

Options:
  --file <path>     Path to README file (default: project root README.md)
  --check-external  Also validate external URLs (slower, requires network)
  --verbose, -v     Show all links, not just broken ones
  --help, -h        Show this help message

Exit Codes:
  0 - All links valid
  1 - Broken links found or error

Examples:
  node validate-links.js                    # Check project README
  node validate-links.js --verbose          # Show all links with status
  node validate-links.js --check-external   # Also validate external URLs
`);
}

/**
 * Extract all markdown links from content
 * @param {string} content - Markdown content
 * @returns {Array<Object>} Array of link objects with text, url, line
 */
function extractLinks(content) {
  const links = [];
  const lines = content.split('\n');

  // Match [text](url) pattern
  const linkPattern = /\[([^\]]*)\]\(([^)]+)\)/g;

  // Match reference-style links [text][ref] and [ref]: url
  const refDefPattern = /^\[([^\]]+)\]:\s*(.+)$/;
  const refUsePattern = /\[([^\]]*)\]\[([^\]]+)\]/g;

  // Collect reference definitions first
  const references = new Map();

  for (let i = 0; i < lines.length; i++) {
    const match = lines[i].match(refDefPattern);
    if (match) {
      references.set(match[1].toLowerCase(), {
        url: match[2].trim(),
        line: i + 1
      });
    }
  }

  // Extract inline links
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    let match;

    // Reset regex state
    linkPattern.lastIndex = 0;

    while ((match = linkPattern.exec(line)) !== null) {
      links.push({
        text: match[1],
        url: match[2],
        line: i + 1,
        type: 'inline'
      });
    }

    // Extract reference-style link uses
    refUsePattern.lastIndex = 0;

    while ((match = refUsePattern.exec(line)) !== null) {
      const refKey = (match[2] || match[1]).toLowerCase();
      const ref = references.get(refKey);

      if (ref) {
        links.push({
          text: match[1],
          url: ref.url,
          line: i + 1,
          type: 'reference',
          refLine: ref.line
        });
      } else {
        links.push({
          text: match[1],
          url: `[undefined reference: ${refKey}]`,
          line: i + 1,
          type: 'reference',
          broken: true,
          reason: `Reference "${refKey}" not defined`
        });
      }
    }
  }

  return links;
}

/**
 * Extract image references from content
 * @param {string} content - Markdown content
 * @returns {Array<Object>} Array of image objects
 */
function extractImages(content) {
  const images = [];
  const lines = content.split('\n');

  // Match ![alt](url) pattern
  const imgPattern = /!\[([^\]]*)\]\(([^)]+)\)/g;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    let match;

    imgPattern.lastIndex = 0;

    while ((match = imgPattern.exec(line)) !== null) {
      images.push({
        alt: match[1],
        url: match[2],
        line: i + 1,
        type: 'image'
      });
    }
  }

  return images;
}

/**
 * Check if a local file path exists
 * @param {string} url - File path (relative or absolute)
 * @param {string} baseDir - Base directory for relative paths
 * @returns {Object} Validation result
 */
function checkLocalPath(url, baseDir) {
  // Handle anchor-only links
  if (url.startsWith('#')) {
    return { valid: true, type: 'anchor' };
  }

  // Strip anchor from URL for file check
  const urlWithoutAnchor = url.split('#')[0];

  // Skip empty paths
  if (!urlWithoutAnchor) {
    return { valid: true, type: 'anchor' };
  }

  // Resolve path
  let resolvedPath;
  if (path.isAbsolute(urlWithoutAnchor)) {
    resolvedPath = urlWithoutAnchor;
  } else {
    resolvedPath = path.join(baseDir, urlWithoutAnchor);
  }

  // Check if file or directory exists
  try {
    fs.accessSync(resolvedPath, fs.constants.R_OK);
    return { valid: true, type: 'local', path: resolvedPath };
  } catch (err) {
    return {
      valid: false,
      type: 'local',
      path: resolvedPath,
      reason: 'File not found'
    };
  }
}

/**
 * Check if an external URL is reachable
 * @param {string} url - URL to check
 * @returns {Promise<Object>} Validation result
 */
function checkExternalUrl(url) {
  return new Promise((resolve) => {
    try {
      const parsed = new URL(url);
      const client = parsed.protocol === 'https:' ? https : http;

      const req = client.request(url, { method: 'HEAD', timeout: 10000 }, (res) => {
        const valid = res.statusCode >= 200 && res.statusCode < 400;
        resolve({
          valid,
          type: 'external',
          statusCode: res.statusCode,
          reason: valid ? null : `HTTP ${res.statusCode}`
        });
      });

      req.on('error', (err) => {
        resolve({
          valid: false,
          type: 'external',
          reason: err.message
        });
      });

      req.on('timeout', () => {
        req.destroy();
        resolve({
          valid: false,
          type: 'external',
          reason: 'Request timeout'
        });
      });

      req.end();
    } catch (err) {
      resolve({
        valid: false,
        type: 'external',
        reason: `Invalid URL: ${err.message}`
      });
    }
  });
}

/**
 * Determine if a URL is external
 * @param {string} url - URL to check
 * @returns {boolean} True if external
 */
function isExternalUrl(url) {
  return url.startsWith('http://') ||
         url.startsWith('https://') ||
         url.startsWith('//');
}

/**
 * Validate all links in a markdown file
 * @param {string} filepath - Path to markdown file
 * @param {Object} options - Validation options
 * @returns {Promise<Object>} Validation results
 */
async function validateLinks(filepath, options) {
  // Read file
  let content;
  try {
    content = fs.readFileSync(filepath, 'utf8');
  } catch (err) {
    console.error(`Error reading file: ${err.message}`);
    process.exit(1);
  }

  const baseDir = path.dirname(filepath);

  // Extract links and images
  const links = extractLinks(content);
  const images = extractImages(content);
  const allItems = [...links, ...images];

  console.log(`Found ${links.length} links and ${images.length} images\n`);

  const results = {
    total: allItems.length,
    valid: 0,
    broken: [],
    skipped: 0,
    external: 0
  };

  // Validate each item
  for (const item of allItems) {
    // Skip already marked as broken (e.g., undefined references)
    if (item.broken) {
      results.broken.push(item);
      continue;
    }

    const url = item.url;

    if (isExternalUrl(url)) {
      results.external++;

      if (options.checkExternal) {
        const result = await checkExternalUrl(url);
        if (result.valid) {
          results.valid++;
          if (options.verbose) {
            console.log(`  [OK] ${url} (${result.statusCode || 'ok'})`);
          }
        } else {
          item.reason = result.reason;
          results.broken.push(item);
          console.log(`  [BROKEN] ${url}`);
          console.log(`           Line ${item.line}: ${result.reason}`);
        }
      } else {
        results.skipped++;
        if (options.verbose) {
          console.log(`  [SKIP] ${url} (external)`);
        }
      }
    } else {
      // Local path
      const result = checkLocalPath(url, baseDir);

      if (result.valid) {
        results.valid++;
        if (options.verbose) {
          console.log(`  [OK] ${url} (${result.type})`);
        }
      } else {
        item.reason = result.reason;
        item.resolvedPath = result.path;
        results.broken.push(item);
        console.log(`  [BROKEN] ${url}`);
        console.log(`           Line ${item.line}: ${result.reason}`);
        if (result.path) {
          console.log(`           Resolved: ${result.path}`);
        }
      }
    }
  }

  return results;
}

/**
 * Print summary of validation results
 * @param {Object} results - Validation results
 */
function printSummary(results) {
  console.log('\n--- Summary ---\n');
  console.log(`  Total items:    ${results.total}`);
  console.log(`  Valid:          ${results.valid}`);
  console.log(`  Broken:         ${results.broken.length}`);
  console.log(`  External:       ${results.external}`);
  console.log(`  Skipped:        ${results.skipped}`);

  if (results.broken.length > 0) {
    console.log('\n--- Broken Links ---\n');
    for (const item of results.broken) {
      const type = item.type === 'image' ? 'Image' : 'Link';
      console.log(`  ${type} on line ${item.line}:`);
      console.log(`    Text: "${item.text || item.alt || '(no text)'}"`);
      console.log(`    URL:  ${item.url}`);
      console.log(`    Reason: ${item.reason}`);
      console.log('');
    }
  }
}

/**
 * Main entry point
 */
async function main() {
  const options = parseArgs();

  if (options.help) {
    showHelp();
    process.exit(0);
  }

  // Determine file to check
  const filepath = options.file || path.join(PROJECT_ROOT, 'README.md');

  // Check file exists
  if (!fs.existsSync(filepath)) {
    console.error(`File not found: ${filepath}`);
    process.exit(1);
  }

  console.log(`Validating links in: ${filepath}\n`);

  if (!options.checkExternal) {
    console.log('Note: External URLs are skipped. Use --check-external to validate them.\n');
  }

  const results = await validateLinks(filepath, options);
  printSummary(results);

  // Exit with error if broken links found
  if (results.broken.length > 0) {
    console.log(`\nValidation FAILED: ${results.broken.length} broken link(s) found.`);
    process.exit(1);
  } else {
    console.log('\nValidation PASSED: All links are valid.');
    process.exit(0);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

// Export for testing
module.exports = {
  extractLinks,
  extractImages,
  checkLocalPath,
  isExternalUrl,
  parseArgs
};
