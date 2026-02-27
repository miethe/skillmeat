## CLI Reference

SkillMeat provides a comprehensive CLI with 116+ commands organized into functional groups.

### Core Commands

| Command | Description |
|---------|-------------|
| `init` | Initialize a new collection |
| `list` | List all artifacts in your collection |
| `show <artifact>` | Show detailed information about an artifact |
| `add skill/command/agent <source>` | Add artifacts from GitHub or local sources |
| `deploy <artifact>` | Deploy artifact to a project |
| `remove <artifact>` | Remove artifact from collection |

### Sync & Intelligence

| Command | Description |
|---------|-------------|
| `sync check` | Check for drift between collection and deployments |
| `sync pull` | Pull changes from upstream sources |
| `sync preview` | Preview changes before applying |
| `search <query>` | Search across all projects and collections |
| `find-duplicates` | Find similar or duplicate artifacts |
| `similar <artifact>` | Find similar artifacts with options: --limit, --min-score, --source |
| `consolidate` | Interactive duplicate consolidation wizard (options: --min-score, --limit, --non-interactive, --output) |

### Advanced Features

{{> command-list}}

For complete CLI documentation, see the [CLI Reference Guide](docs/cli-reference.md).
