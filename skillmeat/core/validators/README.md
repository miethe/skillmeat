# Context Entity Validators

Validation module for all 5 context entity types used in the Agent Context Entities feature.

## Entity Types

1. **ProjectConfig** (`CLAUDE.md`)
   - Valid markdown content
   - Optional YAML frontmatter
   - Must not be empty

2. **SpecFile** (`.claude/specs/`)
   - YAML frontmatter REQUIRED with `title` field
   - Path must start with `.claude/specs/`
   - Valid markdown content after frontmatter

3. **RuleFile** (`.claude/rules/`)
   - Valid markdown content
   - Path must start with `.claude/rules/`
   - Optional `<!-- Path Scope: ... -->` comment

4. **ContextFile** (`.claude/context/`)
   - YAML frontmatter REQUIRED with `references:` list
   - Path must start with `.claude/context/`
   - Valid markdown content after frontmatter

5. **ProgressTemplate** (`.claude/progress/`)
   - YAML frontmatter REQUIRED with `type: progress` field
   - Path must start with `.claude/progress/`
   - YAML+Markdown hybrid format

## Security Features

All validators include path traversal prevention:
- No `..` in paths
- No absolute paths
- Paths starting with `.claude/` cannot escape that directory

## Usage

```python
from skillmeat.core.validators import validate_context_entity

# Validate a spec file
content = """---
title: My Specification
description: This is a spec
---

# Specification Content

Details here...
"""

errors = validate_context_entity(
    entity_type='spec_file',
    content=content,
    path='.claude/specs/my-spec.md'
)

if errors:
    print(f"Validation failed with {len(errors)} errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print("Validation successful!")
```

## Individual Validators

You can also import and use individual validators:

```python
from skillmeat.core.validators import (
    validate_project_config,
    validate_spec_file,
    validate_rule_file,
    validate_context_file,
    validate_progress_template,
)

# Use specific validator
errors = validate_spec_file(content, path)
```

## Return Format

All validators return a list of error messages (strings):
- Empty list `[]` = validation successful
- Non-empty list = validation failed, contains error messages

## Examples

### Valid Spec File

```python
content = """---
title: API Design
description: REST API patterns
---

# API Design Spec

...
"""

errors = validate_context_entity('spec_file', content, '.claude/specs/api-design.md')
# errors = []  # Valid!
```

### Invalid Spec File (Missing Title)

```python
content = """---
description: Missing title
---

# Content
"""

errors = validate_context_entity('spec_file', content, '.claude/specs/invalid.md')
# errors = ["Frontmatter must include 'title' field"]
```

### Path Traversal Attack

```python
content = "# Valid content"

errors = validate_context_entity('project_config', content, '../../../etc/passwd')
# errors = ["Path contains parent directory reference (..) - security risk"]
```

## Error Messages

Common error messages:
- `Content cannot be empty`
- `YAML frontmatter is required but not found`
- `Frontmatter must include 'title' field`
- `Frontmatter must include 'references' field`
- `'references' field must be a list`
- `Frontmatter 'type' field must be 'progress'`
- `Path must start with .claude/specs/` (or other required prefix)
- `Path contains parent directory reference (..) - security risk`
- `Absolute path detected - must be relative`
- `Content too short to be valid markdown`

## Integration with Storage Layer

These validators will be used by the storage layer when:
1. Adding new context entities to collections
2. Importing context entities from repositories
3. Validating entity content before persistence
4. API endpoints accepting entity content

See Phase 1, TASK-1.4 (Storage Layer) for integration patterns.
