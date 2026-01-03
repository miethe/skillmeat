# MeatyCapture Integration Spec

Design specification for integrating the meatycapture-capture skill into project workflows. Use this spec during skill deployment to configure target projects.

---

## Entry Points (Token Efficiency)

MeatyCapture provides two entry points optimized for different use cases:

| Entry Point | Use Case | Tokens | When to Use |
|-------------|----------|-------:|-------------|
| `/mc` command | list, view, search, quick capture | ~150 | Simple operations (95% of use cases) |
| `meatycapture-capture` skill | batch capture, complex workflows | ~400 | Batch operations, validation, templates |

**Default to `/mc`** for all simple operations. Only invoke the full skill when you need:
- Batch capture of multiple items
- Access to workflow documentation
- Item validation via scripts
- Template-based capture

### File Structure

```
.claude/skills/meatycapture-capture/
├── SKILL.md                      # 30 lines - command router
├── skill-config.yaml             # Project defaults
├── workflows/                    # Load only when needed
│   ├── capturing.md              # Batch capture, validation
│   ├── viewing.md                # Advanced filters, output formats
│   ├── updating.md               # Status transitions
│   └── managing.md               # Project configuration
├── references/
│   ├── field-options.md          # Valid field values
│   ├── json-schemas.md           # JSON input schemas
│   └── troubleshooting.md        # Error handling
├── templates/
│   ├── quick-capture.json        # Single item template
│   └── batch-capture.json        # Multi-item template
└── scripts/
    └── validate-items.ts         # Execute-vs-load validation
```

---

## Integration Points

| Trigger | Action | Status Update |
|---------|--------|---------------|
| Bug discovered during development | Capture as type:bug | triage |
| Enhancement identified | Capture as type:enhancement | backlog |
| Technical debt noted | Capture as type:task | backlog |
| Work started on logged item | Update status | in-progress |
| Work completed | Update status | done |
| Item won't be fixed | Update status + note reason | wontfix |

---

## CLAUDE.md Integration

Add minimal section to project's root CLAUDE.md (~10 lines max):

```markdown
## Development Tracking

<!-- MeatyCapture Integration - Project: PROJECT_SLUG -->

Track bugs/enhancements via request-logs (replaces loose TODO comments):

| Entry Point | Use When | Tokens |
|-------------|----------|--------|
| `/mc` | Quick ops: list, search, single capture | ~150 |
| `/meatycapture-capture` skill | Batch capture (3+ items), validation, templates | ~400 |

**Quick reference**: `/mc list PROJECT`, `/mc search "keyword" PROJECT`, `/mc capture {...}`
<!-- End MeatyCapture Integration -->
```

**Key principle**: Don't duplicate skill documentation in CLAUDE.md. The skill and /mc command handle details.

---

## Command Integration Patterns

### Fix Commands (e.g., `/fix:fix-gh-issue`, `/fix:bugfix-commit`)

**After successful fix**, capture for future reference:

```markdown
## Follow-up (after fix merged)

If the bug warrants tracking for patterns/recurrence:
- Use `/mc capture {"title": "...", "type": "bug", "status": "done"}`
- Include: root cause, solution approach, affected files
```

### Development Commands (e.g., `/dev:implement-story`, `/dev:new-feature`)

**Before implementation**, check for related logs:

```markdown
## Context Gathering

Search request-logs for related items:
- `/mc search "feature-keyword" PROJECT`

Reference existing items when relevant to current work.
```

**After implementation**, update any related items:

```markdown
## Post-Implementation

Update status of any request-log items addressed by this work:
- Edit markdown file: change `**Status:** triage` to `**Status:** done`
- For workflow docs, see `./workflows/updating.md`
```

### Planning Commands (e.g., `/plan:plan-feature`, `/plan:spike`)

**During planning**, check existing logs for related items:

```markdown
## Discovery Phase

Query existing request-logs for related bugs/enhancements:
- `/mc search "type:bug" PROJECT`
- `/mc search "domain:web" PROJECT`

Incorporate relevant items into implementation plan.
```

---

## Skill Cross-References

### artifact-tracking Integration

When using `/artifact-tracking` for phase progress:

```markdown
## Task Sources

Reference request-log items in task definitions:
```yaml
tasks:
  - id: "TASK-1.1"
    source: "REQ-20251229-project-03"  # Link to request-log item
    status: "pending"
```
```

### planning Integration

When using `/planning` skill:

```markdown
## Input Sources

Include request-log search in planning discovery (use /mc for token efficiency):
- Bugs: `/mc search "type:bug status:backlog" PROJECT`
- Enhancements: `/mc search "type:enhancement" PROJECT`
```

---

## Generic Integration Patterns

For projects without specific commands, add to CLAUDE.md:

```markdown
## Request Log Workflow

### Quick Operations (use /mc - token efficient)

| Operation | Command |
|-----------|---------|
| List logs | `/mc list PROJECT` |
| View log | `/mc view PATH` |
| Search | `/mc search "keyword" PROJECT` |
| Quick capture | `/mc capture {"title": "...", "type": "bug"}` |

### Batch Operations (use skill when needed)

For batch capture of multiple items, invoke the full skill:
- Use `/meatycapture-capture` for access to templates and validation
- See `./workflows/capturing.md` for batch capture patterns

### Update (during/after work)

Update item status as work progresses:
- Edit markdown file directly
- Change `**Status:** triage` to `**Status:** in-progress` or `done`
```

---

## Init Workflow

When deploying this skill to a new project:

### 1. Copy /mc Command

Copy the `/mc` command to the target project:

```bash
cp .claude/commands/mc.md TARGET_PROJECT/.claude/commands/mc.md
```

### 2. Configure skill-config.yaml

```bash
# Set project default
cat > .claude/skills/meatycapture-capture/skill-config.yaml << 'EOF'
default_project: "project-slug"
auto_detect: true
auto_create_project: true
default_path_pattern: "~/.meatycapture/{project}"
EOF
```

### 3. Add CLAUDE.md Section

Insert the "Development Tracking" section from above into the project's CLAUDE.md. Key points:
- Reference `/mc` for quick operations (token-efficient)
- Reference `/meatycapture-capture` skill for batch/complex operations
- Include example commands with project name

### 4. Identify Integration Points

Scan for existing commands/skills that should integrate:

| Pattern | Integration | Entry Point |
|---------|-------------|-------------|
| `fix/*` commands | Post-fix capture guidance | `/mc capture` |
| `dev/*` commands | Context search + status update | `/mc search` |
| `plan/*` commands | Discovery search | `/mc search` |
| `review/*` commands | Bug capture for findings | `/mc` (1-2 issues) or skill (3+) |

### 5. Update Relevant Commands

For each identified command, add integration snippet using HTML comment markers:

```markdown
<!-- MeatyCapture Integration - Project: PROJECT_SLUG -->
## Section Title

- Integration content here
- Use `/mc` for single operations
- Use skill for batch (3+ items)
<!-- End MeatyCapture Integration -->
```

**Integration pattern benefits**:
- Easy to find: `grep "MeatyCapture Integration" .claude/`
- Easy to update: Project slug in one place
- Clear boundaries: Start/end markers separate from other content
- Minimal tokens: End marker is empty comment (optional for short sections)

---

## Anti-Patterns

| Don't | Instead |
|-------|---------|
| Create TODO comments | Capture to request-log (searchable, trackable) |
| Log every minor fix | Only log patterns worth tracking |
| Duplicate existing items | Search before capture |
| Leave items in triage forever | Review and transition regularly |

---

## Validation

After init, verify integration:

```bash
# Test /mc command works (token-efficient)
/mc list PROJECT
/mc search "test" PROJECT

# Test capture works
/mc capture {"project": "test", "title": "Test", "type": "task"}

# Test project is configured
cat .claude/skills/meatycapture-capture/skill-config.yaml
```

### Token Efficiency Verification

| Entry Point | Expected Tokens | Test |
|-------------|----------------:|------|
| `/mc list` | <200 | Run command, check no skill files loaded |
| `/mc search` | <200 | Run command, check no skill files loaded |
| Skill invocation | <500 | Invoke skill, check only SKILL.md loaded |
| Full workflow | <1,500 | Load workflow file when needed |
