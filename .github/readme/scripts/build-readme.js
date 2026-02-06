#!/usr/bin/env node
/**
 * build-readme.js - Main README assembly script
 *
 * Assembles README.md from partials and data files using Handlebars templating.
 * Loads data from ../data/, partials from ../partials/, and templates from ../templates/.
 *
 * Usage: node build-readme.js [options]
 *
 * Options:
 *   --version <ver>    Override version string in output
 *   --dry-run          Print to stdout instead of writing file
 *   --section <name>   Update only specific section (partial name)
 *   --help             Show help message
 *
 * @example
 *   node build-readme.js                    # Build full README
 *   node build-readme.js --dry-run          # Preview without writing
 *   node build-readme.js --version 0.4.0    # Override version
 */

const fs = require('fs');
const path = require('path');

// Script directory for relative paths
const SCRIPT_DIR = __dirname;
const README_DIR = path.join(SCRIPT_DIR, '..');
const PROJECT_ROOT = path.join(README_DIR, '..', '..');

/**
 * Parse command line arguments
 * @returns {Object} Parsed arguments
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const options = {
    version: null,
    dryRun: false,
    section: null,
    help: false
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--version':
        options.version = args[++i];
        break;
      case '--dry-run':
        options.dryRun = true;
        break;
      case '--section':
        options.section = args[++i];
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
build-readme.js - Assemble README.md from partials and data

Usage: node build-readme.js [options]

Options:
  --version <ver>    Override version string in output
  --dry-run          Print to stdout instead of writing file
  --section <name>   Update only specific section (partial name)
  --help, -h         Show this help message

Examples:
  node build-readme.js                    # Build full README
  node build-readme.js --dry-run          # Preview without writing
  node build-readme.js --version 0.4.0    # Override version
  node build-readme.js --section hero     # Build only hero section
`);
}

/**
 * Load JSON data file with error handling
 * @param {string} filename - Name of JSON file in data directory
 * @returns {Object} Parsed JSON data
 */
function loadData(filename) {
  const filepath = path.join(README_DIR, 'data', filename);
  try {
    const content = fs.readFileSync(filepath, 'utf8');
    return JSON.parse(content);
  } catch (err) {
    if (err.code === 'ENOENT') {
      console.error(`Data file not found: ${filepath}`);
    } else if (err instanceof SyntaxError) {
      console.error(`Invalid JSON in ${filename}: ${err.message}`);
    } else {
      console.error(`Error loading ${filename}: ${err.message}`);
    }
    process.exit(1);
  }
}

/**
 * Load and register all partials with Handlebars
 * Loads .md files from partials/ and .hbs files from templates/ (excluding README.hbs)
 * @param {Object} Handlebars - Handlebars instance
 * @returns {Object} Map of partial names to content
 */
function loadPartials(Handlebars) {
  const partialsDir = path.join(README_DIR, 'partials');
  const templatesDir = path.join(README_DIR, 'templates');
  const partials = {};

  // Load .md content partials from partials/
  if (fs.existsSync(partialsDir)) {
    const mdFiles = fs.readdirSync(partialsDir);

    for (const file of mdFiles) {
      if (!file.endsWith('.md')) continue;

      const name = path.basename(file, '.md');
      const filepath = path.join(partialsDir, file);

      try {
        const content = fs.readFileSync(filepath, 'utf8');
        Handlebars.registerPartial(name, content);
        partials[name] = content;
      } catch (err) {
        console.error(`Error loading partial ${file}: ${err.message}`);
        process.exit(1);
      }
    }
  } else {
    console.warn(`Partials directory not found: ${partialsDir}`);
    console.warn('Creating empty partials directory...');
    fs.mkdirSync(partialsDir, { recursive: true });
  }

  // Load .hbs structural partials from templates/ (excluding README.hbs)
  if (fs.existsSync(templatesDir)) {
    const hbsFiles = fs.readdirSync(templatesDir);

    for (const file of hbsFiles) {
      if (!file.endsWith('.hbs')) continue;
      if (file === 'README.hbs') continue; // Skip main template

      const name = path.basename(file, '.hbs');
      const filepath = path.join(templatesDir, file);

      try {
        const content = fs.readFileSync(filepath, 'utf8');
        Handlebars.registerPartial(name, content);
        partials[name] = content;
      } catch (err) {
        console.error(`Error loading template partial ${file}: ${err.message}`);
        process.exit(1);
      }
    }
  }

  return partials;
}

/**
 * Register custom Handlebars helpers
 * @param {Object} Handlebars - Handlebars instance
 */
function registerHelpers(Handlebars) {
  // Format date helper
  Handlebars.registerHelper('formatDate', function(date) {
    if (!date) return '';
    const d = new Date(date);
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  });

  // ISO date helper
  Handlebars.registerHelper('isoDate', function() {
    return new Date().toISOString();
  });

  // Filter array helper
  Handlebars.registerHelper('filter', function(array, key, value, options) {
    if (!Array.isArray(array)) return [];
    return array.filter(item => item[key] === value);
  });

  // Conditional equality helper
  Handlebars.registerHelper('eq', function(a, b) {
    return a === b;
  });

  // Count array items helper
  Handlebars.registerHelper('count', function(array) {
    return Array.isArray(array) ? array.length : 0;
  });

  // Join array with separator
  Handlebars.registerHelper('join', function(array, separator) {
    if (!Array.isArray(array)) return '';
    return array.join(typeof separator === 'string' ? separator : ', ');
  });

  // Check if number is odd (for table row alternating)
  Handlebars.registerHelper('isOdd', function(value) {
    return value % 2 === 1;
  });

  // Get highlighted features across all categories
  Handlebars.registerHelper('highlightedFeatures', function(categories) {
    if (!Array.isArray(categories)) return [];
    const highlighted = [];
    for (const category of categories) {
      if (Array.isArray(category.features)) {
        for (const feature of category.features) {
          if (feature.highlight) {
            highlighted.push({ ...feature, category: category.name });
          }
        }
      }
    }
    return highlighted;
  });

  // Filter screenshots by category
  Handlebars.registerHelper('screenshotsByCategory', function(screenshots, category) {
    if (!Array.isArray(screenshots)) return [];
    return screenshots.filter(s => s.category === category && s.status !== 'pending');
  });

  // Get feature count
  Handlebars.registerHelper('totalFeatures', function(categories) {
    if (!Array.isArray(categories)) return 0;
    return categories.reduce((sum, cat) => sum + (cat.features?.length || 0), 0);
  });

  // Check if any feature in array has a CLI command
  Handlebars.registerHelper('hasCliCommands', function(features) {
    if (!Array.isArray(features)) return false;
    return features.some(feature => feature.cliCommand);
  });

  // Render only CLI commands from a feature array, joined by commas.
  Handlebars.registerHelper('cliCommands', function(features) {
    if (!Array.isArray(features)) return '';
    return features
      .filter(feature => feature && feature.cliCommand)
      .map(feature => `\`${feature.cliCommand}\``)
      .join(', ');
  });
}

/**
 * Load and compile the main template
 * @param {Object} Handlebars - Handlebars instance
 * @returns {Function} Compiled template function
 */
function loadTemplate(Handlebars) {
  const templatePath = path.join(README_DIR, 'templates', 'README.hbs');

  // Check if template exists
  if (!fs.existsSync(templatePath)) {
    console.error(`Template not found: ${templatePath}`);
    console.error('Please create README.hbs template in the templates directory.');
    process.exit(1);
  }

  try {
    const template = fs.readFileSync(templatePath, 'utf8');
    return Handlebars.compile(template);
  } catch (err) {
    console.error(`Error loading template: ${err.message}`);
    process.exit(1);
  }
}

/**
 * Build the README from template and data
 * @param {Object} options - Build options
 * @returns {string} Rendered README content
 */
function buildReadme(options) {
  // Try to load Handlebars
  let Handlebars;
  try {
    Handlebars = require('handlebars');
  } catch (err) {
    console.error('Handlebars not found. Please install it:');
    console.error('  npm install handlebars');
    process.exit(1);
  }

  // Load data files
  console.log('Loading data files...');
  const features = loadData('features.json');
  const screenshots = loadData('screenshots.json');
  const version = loadData('version.json');

  // Apply version override if provided
  if (options.version) {
    version.current = options.version;
  }

  // Register helpers
  registerHelpers(Handlebars);

  // Load partials
  console.log('Loading partials...');
  const partials = loadPartials(Handlebars);
  console.log(`  Loaded ${Object.keys(partials).length} partial(s)`);

  // Load and compile template
  console.log('Compiling template...');
  const template = loadTemplate(Handlebars);

  // Prepare context data
  const context = {
    features: features.categories,
    featureStats: features.stats,
    artifactTypes: features.artifactTypes,
    screenshots: screenshots.screenshots,
    gifs: screenshots.gifs,
    version: version.current,
    releaseDate: version.releaseDate,
    previousVersions: version.previousVersions,
    upcoming: version.upcoming,
    generated: new Date().toISOString(),
    // Convenience accessors
    readmeScreenshots: screenshots.screenshots.filter(s => s.category === 'readme'),
    capturedScreenshots: screenshots.screenshots.filter(s => s.status === 'captured'),
    pendingScreenshots: screenshots.screenshots.filter(s => s.status === 'pending')
  };

  // Render template
  console.log('Rendering README...');
  return template(context);
}

/**
 * Write the README to the project root
 * @param {string} content - README content
 * @param {boolean} dryRun - If true, print to stdout instead
 */
function writeReadme(content, dryRun) {
  if (dryRun) {
    console.log('\n--- DRY RUN OUTPUT ---\n');
    console.log(content);
    console.log('\n--- END DRY RUN ---\n');
    return;
  }

  const outputPath = path.join(PROJECT_ROOT, 'README.md');

  try {
    fs.writeFileSync(outputPath, content, 'utf8');
    console.log(`README.md written to ${outputPath}`);

    // Show stats
    const lines = content.split('\n').length;
    const size = Buffer.byteLength(content, 'utf8');
    console.log(`  Lines: ${lines}`);
    console.log(`  Size: ${(size / 1024).toFixed(2)} KB`);
  } catch (err) {
    console.error(`Error writing README: ${err.message}`);
    process.exit(1);
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

  console.log('Building README.md...\n');

  // Handle section-only build (future feature)
  if (options.section) {
    console.warn(`Section-only build (${options.section}) not yet implemented.`);
    console.warn('Building full README instead.');
  }

  const content = buildReadme(options);
  writeReadme(content, options.dryRun);

  console.log('\nBuild complete!');
}

// Run if called directly
if (require.main === module) {
  main();
}

// Export for testing
module.exports = {
  buildReadme,
  loadData,
  parseArgs
};
