---
title: 'Phase 0: Enums & Foundations'
description: Platform and Tool enums, frontend type definitions, Artifact model updates
created: 2026-01-21
updated: 2026-01-21
status: inferred_complete
---
# Phase 0: Enums & Foundations

**Duration**: 1 week
**Dependencies**: None
**Assigned Subagent(s)**: python-backend-engineer (Opus), ui-engineer-enhanced (Opus), backend-architect (Opus)

## Phase Overview

Establish the foundational types and enums needed for all downstream work. This includes defining the Platform and Tool enums in Python, creating TypeScript mirror types, and updating Artifact models in both backend and frontend.

---

## Task Breakdown

### ENUM-001: Define Platform & Tool Enums (Backend)

**Duration**: 2 days
**Effort**: 3 story points
**Assigned**: python-backend-engineer
**Dependencies**: None

#### Description

Create `skillmeat/core/enums.py` with complete Platform and Tool enums based on Claude Code reference. Tool enum must include all 17 tools currently supported.

#### Acceptance Criteria

- [ ] File `skillmeat/core/enums.py` created
- [ ] `Platform` enum defined with values: CLAUDE_CODE, CURSOR, OTHER
- [ ] `Tool` enum defined with all 17 Claude Code tools:
  - AskUserQuestion, Bash, TaskOutput, Edit, ExitPlanMode, Glob, Grep, KillShell, MCPSearch, NotebookEdit, Read, Skill, Task, TodoWrite, WebFetch, WebSearch, Write
- [ ] Enum values are string-based (e.g., Tool.BASH.value == "Bash")
- [ ] Enums inherit from `str, Enum` for JSON serialization
- [ ] Docstrings explain purpose and usage of each enum
- [ ] No breaking changes to existing imports

#### Implementation Notes

```python
# skillmeat/core/enums.py
from enum import Enum

class Platform(str, Enum):
    """Supported platforms for artifact execution"""
    CLAUDE_CODE = "claude_code"
    CURSOR = "cursor"
    OTHER = "other"

class Tool(str, Enum):
    """Claude Code tools that can be used by agents/skills"""
    ASK_USER_QUESTION = "AskUserQuestion"
    BASH = "Bash"
    TASK_OUTPUT = "TaskOutput"
    EDIT = "Edit"
    EXIT_PLAN_MODE = "ExitPlanMode"
    GLOB = "Glob"
    GREP = "Grep"
    KILL_SHELL = "KillShell"
    MCP_SEARCH = "MCPSearch"
    NOTEBOOK_EDIT = "NotebookEdit"
    READ = "Read"
    SKILL = "Skill"
    TASK = "Task"
    TODO_WRITE = "TodoWrite"
    WEB_FETCH = "WebFetch"
    WEB_SEARCH = "WebSearch"
    WRITE = "Write"
```

#### Definition of Done

- [ ] Enums defined and tested in isolation
- [ ] Can import: `from skillmeat.core.enums import Platform, Tool`
- [ ] JSON serialization works: `json.dumps({"tool": Tool.BASH})`
- [ ] All 17 tools enumerated exactly
- [ ] No typos in tool names (match Claude Code reference exactly)

---

### ENUM-002: Create Frontend Type Definitions

**Duration**: 1 day
**Effort**: 2 story points
**Assigned**: ui-engineer-enhanced
**Dependencies**: ENUM-001 (for reference, not strictly required)

#### Description

Create `skillmeat/web/types/enums.ts` that mirrors the backend Platform and Tool enums, ensuring frontend and backend are in sync.

#### Acceptance Criteria

- [ ] File `skillmeat/web/types/enums.ts` created
- [ ] `Platform` enum mirrors backend with identical values
- [ ] `Tool` enum mirrors backend with identical values
- [ ] Both enums exported as named exports
- [ ] TypeScript compilation passes (no type errors)
- [ ] Can import: `import { Platform, Tool } from '@/types/enums'`
- [ ] Values match backend exactly (case-sensitive)

#### Implementation Notes

```typescript
// skillmeat/web/types/enums.ts
export enum Platform {
  CLAUDE_CODE = 'claude_code',
  CURSOR = 'cursor',
  OTHER = 'other',
}

export enum Tool {
  ASK_USER_QUESTION = 'AskUserQuestion',
  BASH = 'Bash',
  TASK_OUTPUT = 'TaskOutput',
  EDIT = 'Edit',
  EXIT_PLAN_MODE = 'ExitPlanMode',
  GLOB = 'Glob',
  GREP = 'Grep',
  KILL_SHELL = 'KillShell',
  MCP_SEARCH = 'MCPSearch',
  NOTEBOOK_EDIT = 'NotebookEdit',
  READ = 'Read',
  SKILL = 'Skill',
  TASK = 'Task',
  TODO_WRITE = 'TodoWrite',
  WEB_FETCH = 'WebFetch',
  WEB_SEARCH = 'WebSearch',
  WRITE = 'Write',
}
```

#### Definition of Done

- [ ] File location: `skillmeat/web/types/enums.ts`
- [ ] TypeScript compiler happy (no errors/warnings)
- [ ] Export valid (can import both enums)
- [ ] All 17 tools present
- [ ] Values match backend exactly
- [ ] Can use in type annotations: `const tools: Tool[] = [Tool.BASH, Tool.READ]`

---

### ENUM-003: Update Artifact Models

**Duration**: 2 days
**Effort**: 3 story points
**Assigned**: python-backend-engineer (backend), ui-engineer-enhanced (frontend) - parallel
**Dependencies**: ENUM-001, ENUM-002

#### Description

Update both backend and frontend Artifact models to include `tools` field. This includes updating ArtifactMetadata dataclass in Python and ArtifactMetadata interface in TypeScript.

#### Acceptance Criteria

**Backend (Python)**:
- [ ] `skillmeat/core/artifact.py`: ArtifactMetadata updated with `tools: List[Tool]` field
- [ ] Default value: `field(default_factory=list)`
- [ ] Import `Tool` from `skillmeat.core.enums`
- [ ] Artifact dataclass updated if necessary
- [ ] `to_dict()` serialization includes tools as list of string values
- [ ] `from_dict()` deserialization handles tools field

**Frontend (TypeScript)**:
- [ ] `skillmeat/web/types/artifact.ts`: ArtifactMetadata interface updated with `tools?: Tool[]`
- [ ] Field is optional (use `?` syntax)
- [ ] Import `Tool` from `@/types/enums`
- [ ] Type checking passes: `const art: Artifact = { ..., tools: [Tool.BASH] }`
- [ ] API type generation includes new field

#### Implementation Notes

**Python changes**:
```python
# skillmeat/core/artifact.py
from dataclasses import dataclass, field
from skillmeat.core.enums import Tool

@dataclass
class ArtifactMetadata:
    title: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    license: Optional[str] = None
    version: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)  # NEW
    extra: Dict[str, Any] = field(default_factory=dict)
```

**TypeScript changes**:
```typescript
// skillmeat/web/types/artifact.ts
import { Tool } from './enums';

export interface ArtifactMetadata {
  title?: string;
  description?: string;
  license?: string;
  author?: string;
  version?: string;
  tags?: string[];
  tools?: Tool[];  // NEW
}
```

#### Definition of Done

- [ ] Backend: `from skillmeat.core.artifact import ArtifactMetadata` works
- [ ] Backend: `metadata.tools` is list of Tool enums
- [ ] Backend: Serialization preserves tool values as strings
- [ ] Frontend: `import { ArtifactMetadata } from '@/types/artifact'` works
- [ ] Frontend: `artifact.tools` properly typed
- [ ] Both: No circular import issues
- [ ] Tests verify serialization round-trips correctly

---

## Phase 0 Quality Gates

Before proceeding to Phase 1, verify:

### Code Quality
- [ ] All enums defined with proper docstrings
- [ ] No unused imports or dead code
- [ ] Follows project code style conventions

### Type Safety
- [ ] Backend enums inherit from `str, Enum`
- [ ] Frontend enums are proper TypeScript enums
- [ ] Type checking passes (Python mypy, TypeScript tsc)
- [ ] No circular import dependencies

### Consistency
- [ ] All 17 tools enumerated identically in Python and TypeScript
- [ ] Platform values match exactly (case-sensitive)
- [ ] Tool values match Claude Code reference exactly (e.g., "Bash" not "bash")
- [ ] Enum names consistent (Tool, not Tools)

### Testing
- [ ] Enum serialization/deserialization tested
- [ ] All enum values present and valid
- [ ] Invalid enum values properly rejected in validation
- [ ] Type safety verified for tool lists

### Documentation
- [ ] Enums documented with purpose and usage
- [ ] Claude Code tool reference cited
- [ ] Comments explain why 17 tools (and when new tools added)

---

## Risk Assessment

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Tool enum mismatch with Claude Code | Low | High | Verify against official Claude Code tool list; double-check spelling |
| Circular imports between enums and models | Medium | High | Keep enums in separate `enums.py` file; import in models |
| Frontend/backend enum mismatch | Low | High | Create test verifying 1:1 enum correspondence |

### Schedule Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Enum scope creeps to include attributes | Low | Medium | Stick to name and string value only |
| Bikeshedding on enum naming | Low | Low | Use Claude Code official names exactly |

---

## Success Criteria Summary

**Enums Defined**: Platform with 3 values, Tool with 17 values
**Frontend Types**: Mirror backend exactly
**Model Updates**: Both Python and TypeScript include `tools` field
**No Regressions**: Existing artifact imports unaffected

---

## Next Steps

Once Phase 0 is complete:
1. Proceed to Phase 1: Backend Extraction & Caching
2. Phase 0 tasks unblock all downstream work
3. Begin Phase 1 parallel work as soon as ENUM-003 complete
