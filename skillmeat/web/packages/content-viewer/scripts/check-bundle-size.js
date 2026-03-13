#!/usr/bin/env node
/**
 * Source-size guard for @skillmeat/content-viewer
 *
 * Measures the total byte size of TypeScript source files under src/ and
 * exits with code 1 if the aggregate exceeds the configured threshold.
 *
 * This acts as a regression guard — not a production bundle measurement —
 * because the package currently has no build step.  A spike in source size
 * almost always signals a heavy dependency being imported at the top level
 * rather than lazily, which directly translates to bundle regressions in
 * the consuming Next.js app.
 *
 * Usage:
 *   node scripts/check-bundle-size.js
 *   pnpm check-size          (via package.json script)
 */

'use strict';

const fs = require('fs');
const path = require('path');

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/**
 * Maximum allowed aggregate source size in bytes.
 *
 * Baseline at time of guardrail introduction: 85.3 KB across 17 source files.
 * Threshold is set at 110 KB (~29% headroom) to absorb minor additions while
 * still catching large unintentional imports or new heavy components.
 *
 * When adding a new component intentionally, raise this value in the same
 * commit so the change is visible in code review.
 */
const THRESHOLD_BYTES = 110 * 1024;

/** Root of the package (two levels up from scripts/) */
const PACKAGE_ROOT = path.resolve(__dirname, '..');

/** Source directory to measure */
const SRC_DIR = path.join(PACKAGE_ROOT, 'src');

/** File extensions considered source files */
const SOURCE_EXTENSIONS = new Set(['.ts', '.tsx']);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Recursively walk a directory and yield file paths matching the given
 * extension set.  Skips node_modules and __tests__ directories.
 *
 * @param {string} dir
 * @returns {string[]}
 */
function collectSourceFiles(dir) {
  const results = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.name === 'node_modules' || entry.name === '__tests__') {
      continue;
    }

    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      results.push(...collectSourceFiles(fullPath));
    } else if (SOURCE_EXTENSIONS.has(path.extname(entry.name))) {
      results.push(fullPath);
    }
  }

  return results;
}

/**
 * Format a byte count as a human-readable string (e.g., "23.4 KB").
 *
 * @param {number} bytes
 * @returns {string}
 */
function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  return `${kb.toFixed(1)} KB`;
}

/**
 * Compute the relative path from PACKAGE_ROOT for display purposes.
 *
 * @param {string} absolutePath
 * @returns {string}
 */
function relPath(absolutePath) {
  return path.relative(PACKAGE_ROOT, absolutePath);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

function main() {
  if (!fs.existsSync(SRC_DIR)) {
    console.error(`ERROR: src directory not found at ${SRC_DIR}`);
    process.exit(1);
  }

  const files = collectSourceFiles(SRC_DIR);

  if (files.length === 0) {
    console.error('ERROR: No TypeScript source files found under src/');
    process.exit(1);
  }

  // Collect per-file sizes
  const fileSizes = files
    .map((filePath) => ({ filePath, size: fs.statSync(filePath).size }))
    .sort((a, b) => b.size - a.size); // largest first

  const totalBytes = fileSizes.reduce((sum, f) => sum + f.size, 0);

  // Print report
  console.log('\n@skillmeat/content-viewer — source size report');
  console.log('='.repeat(60));

  for (const { filePath, size } of fileSizes) {
    const label = relPath(filePath).padEnd(50);
    const sizeLabel = formatBytes(size).padStart(9);
    console.log(`  ${label}${sizeLabel}`);
  }

  console.log('-'.repeat(60));

  const totalLabel = 'Total'.padEnd(50);
  const totalSizeLabel = formatBytes(totalBytes).padStart(9);
  const thresholdLabel = formatBytes(THRESHOLD_BYTES);

  console.log(`  ${totalLabel}${totalSizeLabel}`);
  console.log(`  ${'Threshold'.padEnd(50)}${thresholdLabel.padStart(9)}`);
  console.log('='.repeat(60));

  if (totalBytes > THRESHOLD_BYTES) {
    console.error(
      `\nFAIL: Total source size ${formatBytes(totalBytes)} exceeds threshold ${thresholdLabel}.`
    );
    console.error(
      'If this is intentional (new component added), update THRESHOLD_BYTES in scripts/check-bundle-size.js.'
    );
    process.exit(1);
  }

  const headroom = THRESHOLD_BYTES - totalBytes;
  console.log(
    `\nPASS: ${formatBytes(totalBytes)} used, ${formatBytes(headroom)} remaining before threshold.`
  );
  process.exit(0);
}

main();
