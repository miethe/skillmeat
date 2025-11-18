/**
 * Lighthouse performance testing for SkillMeat web interface.
 *
 * This script uses Google Lighthouse to measure:
 * - Performance score
 * - Accessibility score
 * - First Contentful Paint (FCP)
 * - Largest Contentful Paint (LCP)
 * - Time to Interactive (TTI)
 * - Cumulative Layout Shift (CLS)
 *
 * Usage:
 *   node skillmeat/web/tests/performance/lighthouse.js
 *   node skillmeat/web/tests/performance/lighthouse.js --url http://localhost:3000
 */

const fs = require('fs');
const path = require('path');

// Check for required dependencies
let lighthouse, chromeLauncher;
try {
  lighthouse = require('lighthouse');
  chromeLauncher = require('chrome-launcher');
} catch (error) {
  console.error('Error: Required dependencies not installed');
  console.error('Run: npm install --save-dev lighthouse chrome-launcher');
  process.exit(1);
}

// SLA targets
const SLA_TARGETS = {
  performance: 90,      // Lighthouse performance score ≥90
  accessibility: 90,    // Accessibility score ≥90
  fcp: 1500,           // First Contentful Paint <1.5s
  lcp: 2500,           // Largest Contentful Paint <2.5s
  tti: 3500,           // Time to Interactive <3.5s
  cls: 0.1,            // Cumulative Layout Shift <0.1
};

/**
 * Run Lighthouse audit on a URL
 */
async function runLighthouse(url) {
  console.log(`\nRunning Lighthouse audit on: ${url}`);
  console.log('='.repeat(80));

  let chrome;
  try {
    // Launch Chrome
    chrome = await chromeLauncher.launch({
      chromeFlags: ['--headless', '--no-sandbox', '--disable-dev-shm-usage'],
    });

    const options = {
      logLevel: 'error',
      output: ['html', 'json'],
      onlyCategories: ['performance', 'accessibility'],
      port: chrome.port,
      throttlingMethod: 'simulate',
    };

    // Run Lighthouse
    const runnerResult = await lighthouse(url, options);

    // Extract scores
    const { lhr } = runnerResult;
    const scores = {
      performance: lhr.categories.performance.score * 100,
      accessibility: lhr.categories.accessibility.score * 100,
      fcp: lhr.audits['first-contentful-paint'].numericValue,
      lcp: lhr.audits['largest-contentful-paint'].numericValue,
      tti: lhr.audits['interactive'].numericValue,
      cls: lhr.audits['cumulative-layout-shift'].numericValue,
      si: lhr.audits['speed-index'].numericValue,
      tbt: lhr.audits['total-blocking-time'].numericValue,
    };

    return { scores, reports: runnerResult.report };
  } finally {
    if (chrome) {
      await chrome.kill();
    }
  }
}

/**
 * Check if scores meet SLA targets
 */
function checkSLAs(scores) {
  const violations = [];
  const warnings = [];

  // Check performance score
  if (scores.performance < SLA_TARGETS.performance) {
    violations.push({
      metric: 'Performance Score',
      actual: scores.performance.toFixed(0),
      target: SLA_TARGETS.performance,
      unit: '/100',
    });
  } else if (scores.performance < SLA_TARGETS.performance + 5) {
    warnings.push({
      metric: 'Performance Score',
      actual: scores.performance.toFixed(0),
      target: SLA_TARGETS.performance,
      unit: '/100',
    });
  }

  // Check accessibility score
  if (scores.accessibility < SLA_TARGETS.accessibility) {
    violations.push({
      metric: 'Accessibility Score',
      actual: scores.accessibility.toFixed(0),
      target: SLA_TARGETS.accessibility,
      unit: '/100',
    });
  }

  // Check FCP
  if (scores.fcp > SLA_TARGETS.fcp) {
    violations.push({
      metric: 'First Contentful Paint',
      actual: scores.fcp.toFixed(0),
      target: SLA_TARGETS.fcp,
      unit: 'ms',
    });
  }

  // Check LCP
  if (scores.lcp > SLA_TARGETS.lcp) {
    violations.push({
      metric: 'Largest Contentful Paint',
      actual: scores.lcp.toFixed(0),
      target: SLA_TARGETS.lcp,
      unit: 'ms',
    });
  }

  // Check TTI
  if (scores.tti > SLA_TARGETS.tti) {
    violations.push({
      metric: 'Time to Interactive',
      actual: scores.tti.toFixed(0),
      target: SLA_TARGETS.tti,
      unit: 'ms',
    });
  }

  // Check CLS
  if (scores.cls > SLA_TARGETS.cls) {
    violations.push({
      metric: 'Cumulative Layout Shift',
      actual: scores.cls.toFixed(3),
      target: SLA_TARGETS.cls,
      unit: '',
    });
  }

  return { violations, warnings };
}

/**
 * Print results in a formatted table
 */
function printResults(url, scores, slaCheck) {
  console.log(`\nResults for: ${url}`);
  console.log('-'.repeat(80));

  // Core Web Vitals
  console.log('\nCore Web Vitals:');
  console.log(`  Performance Score:  ${scores.performance.toFixed(0)}/100 (target: ≥${SLA_TARGETS.performance})`);
  console.log(`  Accessibility:      ${scores.accessibility.toFixed(0)}/100 (target: ≥${SLA_TARGETS.accessibility})`);

  // Detailed metrics
  console.log('\nDetailed Metrics:');
  console.log(`  FCP:                ${scores.fcp.toFixed(0)}ms (target: <${SLA_TARGETS.fcp}ms)`);
  console.log(`  LCP:                ${scores.lcp.toFixed(0)}ms (target: <${SLA_TARGETS.lcp}ms)`);
  console.log(`  TTI:                ${scores.tti.toFixed(0)}ms (target: <${SLA_TARGETS.tti}ms)`);
  console.log(`  CLS:                ${scores.cls.toFixed(3)} (target: <${SLA_TARGETS.cls})`);
  console.log(`  Speed Index:        ${scores.si.toFixed(0)}ms`);
  console.log(`  Total Blocking:     ${scores.tbt.toFixed(0)}ms`);

  // Warnings
  if (slaCheck.warnings.length > 0) {
    console.log('\n⚠️  Warnings:');
    slaCheck.warnings.forEach((w) => {
      console.log(`  ${w.metric}: ${w.actual}${w.unit} (close to target: ${w.target}${w.unit})`);
    });
  }

  // Violations
  if (slaCheck.violations.length > 0) {
    console.log('\n❌ SLA Violations:');
    slaCheck.violations.forEach((v) => {
      console.log(`  ${v.metric}: ${v.actual}${v.unit} (target: ${v.target}${v.unit})`);
    });
  } else {
    console.log('\n✅ All metrics meet SLA targets');
  }
}

/**
 * Save reports to disk
 */
function saveReports(reports, outputDir) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');

  // Save HTML report
  const htmlPath = path.join(outputDir, `lighthouse-${timestamp}.html`);
  fs.writeFileSync(htmlPath, reports[0]);
  console.log(`\nHTML report saved to: ${htmlPath}`);

  // Save JSON report
  const jsonPath = path.join(outputDir, `lighthouse-${timestamp}.json`);
  fs.writeFileSync(jsonPath, reports[1]);
  console.log(`JSON report saved to: ${jsonPath}`);

  return { htmlPath, jsonPath };
}

/**
 * Main function
 */
async function main() {
  const args = process.argv.slice(2);
  const urlIndex = args.indexOf('--url');
  const baseUrl = urlIndex >= 0 && args[urlIndex + 1] ? args[urlIndex + 1] : 'http://localhost:3000';

  // Pages to test
  const pages = [
    { name: 'Homepage', path: '/' },
    { name: 'Marketplace', path: '/marketplace' },
    { name: 'Collections', path: '/collections' },
  ];

  const outputDir = path.join(__dirname, '../../lighthouse-reports');
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  let hasViolations = false;
  const allResults = [];

  console.log('Lighthouse Performance Testing');
  console.log('='.repeat(80));
  console.log(`Base URL: ${baseUrl}`);
  console.log(`Testing ${pages.length} pages...`);

  for (const page of pages) {
    const url = `${baseUrl}${page.path}`;

    try {
      const { scores, reports } = await runLighthouse(url);
      const slaCheck = checkSLAs(scores);

      printResults(url, scores, slaCheck);

      // Save reports
      const reportPaths = saveReports(reports, outputDir);

      allResults.push({
        page: page.name,
        url,
        scores,
        slaCheck,
        reportPaths,
      });

      if (slaCheck.violations.length > 0) {
        hasViolations = true;
      }
    } catch (error) {
      console.error(`\nError testing ${url}:`, error.message);
      hasViolations = true;
    }
  }

  // Summary
  console.log('\n' + '='.repeat(80));
  console.log('Summary');
  console.log('='.repeat(80));

  const totalViolations = allResults.reduce((sum, r) => sum + r.slaCheck.violations.length, 0);
  const totalWarnings = allResults.reduce((sum, r) => sum + r.slaCheck.warnings.length, 0);

  console.log(`Pages tested: ${allResults.length}`);
  console.log(`Total violations: ${totalViolations}`);
  console.log(`Total warnings: ${totalWarnings}`);

  if (hasViolations) {
    console.log('\n❌ Performance testing FAILED - SLA violations detected');
    process.exit(1);
  } else {
    console.log('\n✅ Performance testing PASSED - All pages meet SLA targets');
    process.exit(0);
  }
}

// Run if executed directly
if (require.main === module) {
  main().catch((error) => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = { runLighthouse, checkSLAs };
