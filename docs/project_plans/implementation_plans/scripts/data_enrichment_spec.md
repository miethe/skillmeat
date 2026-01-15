# Data Enrichment Spec for Codebase Visualizer

**Goal**: Extend the codebase graph data pipeline to include "Git Metadata" and "External Dependencies". This data is consumed by the frontend visualizer to enable "Color By" features (e.g. churn, authorship) and dependency visualization.

**Target Outputs**:
1. `codebase-graph.git-metadata.json`
2. `codebase-graph.dependencies.json`

**Integration**: Run these scripts as part of your data generation pipeline. Ensure the output JSON files are placed in the same directory as [codebase-graph.json](file:///Users/miethe/dev/homelab/development/codebase-map/codebase-graph.json) so the visualizer can load them.

---

## 1. Git Metadata Extractor

**Purpose**: Extracts commit history statistics for each file to visualize "hotspots" and ownership.

**Script ([extract_git_metadata.js](file:///Users/miethe/dev/homelab/development/codebase-map/scripts/extract_git_metadata.js))**:
*Requires Node.js installed.*

```javascript
/* 
   Usage: node extract_git_metadata.js [output_dir]
   Default output: ./codebase-graph.git-metadata.json
*/
import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const outputDir = args[0] || process.cwd();
const OUTPUT_FILE = path.join(outputDir, 'codebase-graph.git-metadata.json');

console.log(`Extracting Git metadata to ${OUTPUT_FILE}...`);

try {
    const filesBuffer = execSync('git ls-files');
    const files = filesBuffer.toString().trim().split('\n');
    
    // git log format: "###TIMESTAMP|AUTHOR"
    const logBuffer = execSync('git log --name-only --format="###%at|%an"');
    const lines = logBuffer.toString().split('\n');

    let currentCommitDate = 0;
    let currentCommitAuthor = '';

    const stats = {}; 

    files.forEach(f => {
        stats[f] = { changes: 0, lastModified: 0, authors: new Set() };
    });

    for (const line of lines) {
        if (!line.trim()) continue;

        if (line.startsWith('###')) {
            const parts = line.substring(3).split('|');
            currentCommitDate = parseInt(parts[0], 10) * 1000; 
            currentCommitAuthor = parts[1];
        } else {
            const filePath = line.trim();
            if (stats[filePath]) {
                const s = stats[filePath];
                s.changes++;
                s.authors.add(currentCommitAuthor);
                if (s.lastModified === 0) {
                    s.lastModified = currentCommitDate;
                }
            }
        }
    }

    const finalMetadata = {};
    for (const [file, s] of Object.entries(stats)) {
        finalMetadata[file] = {
            last_modified: s.lastModified,
            change_count: s.changes,
            unique_authors: s.authors.size,
        };
    }

    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(finalMetadata, null, 2));
    console.log(`Success! Wrote metadata for ${files.length} files.`);

} catch (e) {
    console.error('Error extracting git metadata:', e);
    process.exit(1);
}
```

## 2. Dependency Scanner

**Purpose**: specific usage of external libraries (from [package.json](file:///Users/miethe/dev/homelab/development/codebase-map/package.json) or equivalent) to visualize 3rd-party weight.

**Script ([scan_dependencies.js](file:///Users/miethe/dev/homelab/development/codebase-map/scripts/scan_dependencies.js))**:
*Requires Node.js. Can be adapted for Python/pip requirements.txt.*

```javascript
/* 
   Usage: node scan_dependencies.js [output_dir]
   Default output: ./codebase-graph.dependencies.json
*/
import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const outputDir = args[0] || process.cwd();
const PKG_FILE = path.join(process.cwd(), 'package.json');
const OUTPUT_FILE = path.join(outputDir, 'codebase-graph.dependencies.json');

console.log(`Scanning dependencies from ${PKG_FILE}...`);

try {
    if (!fs.existsSync(PKG_FILE)) {
        console.error('No package.json found!');
        process.exit(0);
    }

    const pkg = JSON.parse(fs.readFileSync(PKG_FILE, 'utf-8'));
    const nodes = [];
    const edges = [];

    const processDeps = (deps, type) => {
        if (!deps) return;
        Object.entries(deps).forEach(([name, version]) => {
            const nodeId = `node_modules/${name}`;
            nodes.push({
                id: nodeId,
                type: 'external_dependency',
                label: name,
                file: 'package.json',
                details: { version, deptype: type },
                modulePath: ['External', type === 'dependencies' ? 'Production' : 'Dev']
            });
        });
    };

    processDeps(pkg.dependencies, 'dependencies');
    processDeps(pkg.devDependencies, 'devDependencies');

    const graph = { nodes, edges }; // Edges can be added if import analysis is available
    fs.writeFileSync(OUTPUT_FILE, JSON.stringify(graph, null, 2));
    console.log(`Success! Wrote ${nodes.length} dependency nodes.`);

} catch (e) {
    console.error('Error scanning dependencies:', e);
    process.exit(1);
}
```

## JSON Schema Reference

### `codebase-graph.git-metadata.json`
```json
{
  "path/to/file.ts": {
    "last_modified": 1715000000000,
    "change_count": 42,
    "unique_authors": 3
  }
}
```

### `codebase-graph.dependencies.json`
```json
{
  "nodes": [
    {
      "id": "node_modules/react",
      "type": "external_dependency",
      "label": "react",
      "file": "package.json",
      "modulePath": ["External", "Production"], 
      "details": { "version": "^18.2.0" }
    }
  ],
  "edges": []
}
```
