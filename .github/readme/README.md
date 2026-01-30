# README Generation System

This directory contains the modular system for generating and maintaining the root README.md file.

## Directory Structure

```
.github/readme/
├── README.md           # This file
├── partials/           # Reusable Markdown content blocks
│   ├── hero.md         # Logo, tagline, badges
│   ├── features.md     # Feature showcase
│   ├── quickstart.md   # Installation & first steps
│   ├── screenshots.md  # Screenshot grid
│   └── ...
├── data/               # Structured data for rendering
│   ├── features.json   # Complete feature definitions
│   ├── screenshots.json # Screenshot metadata & status
│   └── version.json    # Version information
├── templates/          # Handlebars templates
│   └── README.hbs      # Main README template
└── scripts/            # Build and validation scripts
    ├── build-readme.js # Assembles README from partials
    └── validate.js     # Validates links and images
```

## Quick Start

### Build README

```bash
cd .github/readme
npm install
npm run build
```

### Validate Links

```bash
npm run validate
```

### Update Version

```bash
npm run update-version -- --version 0.4.0
```

## Data Files

### features.json

Complete catalog of all SkillMeat features organized by category. Each feature includes:
- `id`: Unique identifier
- `name`: Display name
- `description`: Full description
- `shortDescription`: One-liner for compact displays
- `cliCommand`: Associated CLI command (if any)
- `webPage`: Associated web page path (if any)
- `since`: Version when feature was added
- `screenshot`: Associated screenshot ID
- `highlight`: Whether to feature prominently

### screenshots.json

Metadata for all screenshots and GIFs:
- `id`: Unique identifier
- `file`: Path relative to repo root
- `alt`: Alt text for accessibility
- `width`/`height`: Dimensions
- `category`: readme | features | cli | gifs
- `page`: Web page or context
- `status`: pending | captured | outdated
- `notes`: Capture instructions

### version.json

Version tracking for the README:
- `current`: Current version string
- `releaseDate`: Release date
- `previousVersions`: Version history
- `upcoming`: Planned version info

## Workflows

### Adding a New Feature

1. Add entry to `data/features.json` in appropriate category
2. Capture screenshot if needed (update `screenshots.json`)
3. Run `npm run build`
4. Commit all changes

### Updating Screenshots

1. Start web dev server: `skillmeat web dev`
2. Navigate to target page
3. Use chrome-devtools skill or Claude in Chrome to capture
4. Save to appropriate `docs/screenshots/` subdirectory
5. Update `screenshots.json` with captured date and status
6. Run `npm run build`

### Recording GIFs

Use Claude in Chrome MCP for browser recordings:

```
1. mcp__claude-in-chrome__tabs_context_mcp
2. mcp__claude-in-chrome__navigate to start page
3. mcp__claude-in-chrome__gif_creator action=start_recording
4. mcp__claude-in-chrome__computer action=screenshot (initial frame)
5. [Perform sequence of actions]
6. mcp__claude-in-chrome__computer action=screenshot (final frame)
7. mcp__claude-in-chrome__gif_creator action=stop_recording
8. mcp__claude-in-chrome__gif_creator action=export download=true
```

For CLI recordings, use asciinema:

```bash
asciinema rec cli-demo.cast
# Run commands
# Ctrl+D to stop
agg cli-demo.cast docs/screenshots/gifs/cli-demo.gif
```

## CI Integration

The workflow in `.github/workflows/readme-check.yml` validates:
- All referenced images exist
- All links are valid
- Generated README matches source data
- Screenshot metadata is up to date

## Programmatic Updates

The modular structure enables automated updates:

```javascript
// Example: Add a new feature programmatically
const features = require('./data/features.json');
features.categories[0].features.push({
  id: 'new-feature',
  name: 'New Feature',
  description: 'Description here',
  since: '0.4.0'
});
fs.writeFileSync('./data/features.json', JSON.stringify(features, null, 2));
// Then run build
```

## Best Practices

1. **Never edit README.md directly** - always modify partials/data
2. **Keep screenshots up to date** - mark outdated when UI changes
3. **Use consistent naming** - follow existing ID patterns
4. **Include alt text** - for accessibility
5. **Document capture notes** - so screenshots can be reproduced
