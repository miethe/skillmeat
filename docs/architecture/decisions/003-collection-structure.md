# Decision: Collection File Structure

**Status**: Approved
**Date**: 2025-11-07
**Decider**: Implementation Team

## Context

Need to decide how to organize artifacts within a collection directory. Two main approaches:
1. **Type-organized**: Separate directories for skills, commands, agents
2. **Flat with prefixes**: Single directory with type prefixes in filenames

## Decision

**Use type-organized directory structure** (as specified in implementation plan).

```
~/.skillmeat/collections/default/
├── collection.toml
├── collection.lock
├── skills/
│   ├── python-skill/
│   │   └── SKILL.md
│   └── javascript-helper/
│       └── SKILL.md
├── commands/
│   ├── review.md
│   └── lint-check.md
└── agents/
    ├── code-reviewer.md
    └── security-auditor.md
```

## Rationale

1. **Mirrors Claude Structure**: Matches `.claude/` directory layout users are familiar with
2. **Browsability**: Easy to explore in file manager or terminal
3. **Type Operations**: Natural for type-specific commands (e.g., list all commands)
4. **Backup/Restore**: Can selectively backup by type
5. **Mental Model**: Clear organization by artifact type
6. **Future-Proof**: Easy to add new artifact types (hooks, mcp) as new directories

## Implementation Impact

- **Storage Paths**:
  - Skills: `collections/{name}/skills/{artifact_name}/`
  - Commands: `collections/{name}/commands/{artifact_name}.md`
  - Agents: `collections/{name}/agents/{artifact_name}.md`
- **Deployment**: Direct mapping to `.claude/` structure
- **Artifact.path**: Stored as relative path from collection root (e.g., `skills/python-skill/`)
- **File Operations**: Need to handle both directory (skills) and file (commands/agents) artifacts

## Artifact Storage Rules

| Type | Storage Format | Example |
|------|---------------|---------|
| **Skill** | Directory with SKILL.md | `skills/python-skill/SKILL.md` |
| **Command** | Single .md file | `commands/review.md` |
| **Agent** | Single .md file | `agents/code-reviewer.md` |
| **MCP** (Future) | Directory with config | `mcp/server-name/` |
| **Hook** (Future) | Single script file | `hooks/pre-commit.sh` |

## Deployment Mapping

Collection structure maps 1:1 to project structure:

```
Collection:                          Project:
~/.skillmeat/collections/default/    ~/project/.claude/
├── skills/python-skill/        →    ├── skills/python-skill/
├── commands/review.md          →    ├── commands/review.md
└── agents/code-reviewer.md     →    └── agents/code-reviewer.md
```

## Alternatives Considered

**Option 1: Flat structure with prefixes**
```
~/.skillmeat/collections/default/artifacts/
├── skill-python-skill/
├── command-review.md
└── agent-code-reviewer.md
```
- Rejected: Doesn't mirror `.claude/` structure, harder to browse

**Option 2: Database storage** (SQLite)
- Rejected: Over-engineered for MVP, adds dependency, harder to inspect

**Option 3: Git repo per collection**
- Rejected: Users can optionally Git-track collections, shouldn't be forced
