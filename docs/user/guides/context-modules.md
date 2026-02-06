---
title: Working with Context Modules
description: Complete guide to creating, configuring, and using context modules to compose reusable memory packs for AI agents
audience: [users]
tags: [guide, context-modules, memory, context-packs, ai-agents, workflows]
created: 2026-02-06
updated: 2026-02-06
category: user-guide
status: published
related_documents:
  - /docs/user/guides/memory-context-system.md
  - /docs/user/guides/memory-inbox.md
  - /docs/user/guides/web-ui-guide.md
  - /docs/project_plans/PRDs/features/memory-context-system-v1.md
---

# Working with Context Modules

Context modules are reusable configurations that automatically select and organize memory items into context packs for AI agents. Instead of manually choosing which memories to include each time, you create modules with specific criteria (memory types, confidence levels, file patterns) that dynamically compose the right context for different workflows.

## What are Context Modules?

Context modules transform your memory collection from a static database into an intelligent context delivery system. Each module defines:

- **Selection criteria** (selectors) that filter memories by type, confidence, file paths, or workflow stage
- **Priority** for ordering when multiple modules are composed together
- **Manual inclusions** for memories that should always be included regardless of selectors

This approach provides:

- **Reusability**: Define once, generate context packs on demand
- **Consistency**: Same criteria produce consistent context across sessions
- **Flexibility**: Compose multiple modules together for complex workflows
- **Token efficiency**: Budget-aware selection ensures context fits within limits

## Understanding Selectors

Selectors are the filtering rules that determine which memories a module includes. Each module can use multiple selector types simultaneously.

### Memory Types Selector

Filter memories by their classification type. Useful for workflow-specific context.

**Available Types**:
- **Decision**: Architectural decisions and design choices
- **Constraint**: Technical limitations and requirements
- **Gotcha**: Edge cases, bugs, and workarounds
- **Style Rule**: Code style and formatting conventions
- **Learning**: Patterns discovered during development

**Example Use Cases**:
```
API Design Module:
  Types: [Decision, Constraint]
  Purpose: Include architecture decisions and technical requirements

Debugging Module:
  Types: [Gotcha, Fix]
  Purpose: Include known issues and their solutions

Onboarding Module:
  Types: [Style Rule, Learning]
  Purpose: Include coding conventions and patterns
```

### Minimum Confidence Selector

Filter memories by confidence score (0.0 to 1.0). Higher confidence means the AI extracted the memory with greater certainty.

**Confidence Tiers**:
- **High** (≥ 0.85): Production-ready, verified memories
- **Medium** (0.60-0.84): Likely accurate, may need review
- **Low** (< 0.60): Experimental or uncertain

**Example Configurations**:
```
Production Module:
  Min Confidence: 0.85
  Purpose: Only include verified, high-quality memories

Development Module:
  Min Confidence: 0.60
  Purpose: Include medium-confidence learnings and experiments

Exploratory Module:
  Min Confidence: 0.0 (no filter)
  Purpose: Include all memories regardless of confidence
```

### File Patterns Selector

Filter memories based on the files they reference. Uses glob patterns to match file paths.

**Pattern Syntax**:
- `src/api/**` - All files under src/api/
- `*.tsx` - All TypeScript React files
- `components/ui/*` - Direct children of components/ui/
- `**/*.test.ts` - All test files anywhere

**Example Configurations**:
```
Frontend Module:
  Patterns: ["src/components/**", "src/hooks/**", "*.tsx"]
  Purpose: Include memories related to React components and hooks

Backend Module:
  Patterns: ["src/api/**", "src/services/**", "*.py"]
  Purpose: Include memories related to API and service layers

Testing Module:
  Patterns: ["**/*.test.ts", "**/*.spec.ts", "tests/**"]
  Purpose: Include memories related to test files
```

### Workflow Stages Selector

Filter memories by development workflow stage. Useful for stage-specific context.

**Common Stages**:
- `planning` - Design and architecture phase
- `implementation` - Active development
- `review` - Code review and refinement
- `debugging` - Bug investigation and fixing
- `optimization` - Performance tuning

**Example Configurations**:
```
Planning Module:
  Stages: [planning, review]
  Purpose: Include high-level decisions and constraints

Implementation Module:
  Stages: [implementation, debugging]
  Purpose: Include practical patterns and gotchas
```

### Combining Selectors

All selectors are combined with AND logic - memories must match all configured criteria.

**Example: API Development Module**
```
Name: API Development
Memory Types: [Decision, Constraint, Gotcha]
Min Confidence: 0.70
File Patterns: ["src/api/**", "src/schemas/**"]
Workflow Stages: [implementation, debugging]

Result: Includes only memories that:
  - Are decisions, constraints, or gotchas AND
  - Have confidence ≥ 70% AND
  - Reference files in src/api/ or src/schemas/ AND
  - Are tagged for implementation or debugging stages
```

## Creating Your First Module

### Via Web Interface

The web interface provides a visual workflow for creating modules.

**Step 1: Navigate to Context Modules**
1. Open SkillMeat web interface (`skillmeat web dev`)
2. Select your project from the sidebar
3. Navigate to the **Memory** section
4. Click the **Context Modules** tab

**Step 2: Create New Module**
1. Click **New Module** button (top right)
2. Fill in basic information:
   - **Name**: Descriptive name (e.g., "API Design Decisions")
   - **Description**: Optional explanation of the module's purpose
   - **Priority**: 0-100, higher numbers load first (default: 5)

**Step 3: Configure Selectors**
1. **Memory Types**: Check boxes for types to include
   - Leave all unchecked to include all types
2. **Minimum Confidence**: Drag slider or enter percentage
   - 0% = no filter, 100% = only highest confidence
3. **File Patterns**: Press Enter or comma to add each pattern
   - Example: `src/api/**`, `*.py`
4. **Workflow Stages**: Press Enter or comma to add each stage
   - Example: `implementation`, `debugging`

**Step 4: Save Module**
1. Click **Create Module** button
2. Module appears in the modules list
3. Ready to generate context packs

### Via CLI (Future Feature)

Command-line module creation:

```bash
# Create basic module
skillmeat memory module create "API Design" \
  --project my-project \
  --description "Architecture decisions and constraints for API development"

# Create module with selectors
skillmeat memory module create "Frontend Patterns" \
  --project my-project \
  --types decision,learning \
  --min-confidence 0.75 \
  --patterns "src/components/**" "*.tsx" \
  --priority 8

# Create module for debugging workflow
skillmeat memory module create "Debugging Context" \
  --project my-project \
  --types gotcha,fix \
  --stages debugging \
  --min-confidence 0.60
```

## Configuring Module Selectors

### Basic Configuration: Single Type Filter

Create a module that includes only one type of memory.

**Example: Style Rules Module**
```
Name: Code Style Guide
Description: Coding conventions and formatting rules
Selectors:
  Memory Types: [Style Rule]
  Min Confidence: 0.80
  File Patterns: (none - all files)
  Workflow Stages: (none - all stages)
Priority: 7

Use Case: Generate style guide context when reviewing code
```

### Intermediate Configuration: Multiple Selectors

Combine multiple selector types for focused context.

**Example: API Development Module**
```
Name: API Development
Description: Backend API patterns and constraints
Selectors:
  Memory Types: [Decision, Constraint]
  Min Confidence: 0.70
  File Patterns: ["src/api/**", "src/schemas/**"]
  Workflow Stages: [implementation]
Priority: 8

Use Case: Generate API-specific context during backend development
```

### Advanced Configuration: Comprehensive Module

Use all selector types for highly targeted context.

**Example: Frontend Component Development**
```
Name: Component Development
Description: React component patterns and gotchas
Selectors:
  Memory Types: [Decision, Style Rule, Gotcha]
  Min Confidence: 0.75
  File Patterns: ["src/components/**", "src/hooks/**", "*.tsx"]
  Workflow Stages: [implementation, review]
Priority: 9

Use Case: Generate comprehensive context for React component work
```

### Manual Memory Selection

In addition to automatic selectors, you can manually add specific memories to a module.

**When to Use Manual Selection**:
- Critical memories that must always be included
- Edge cases not captured by selectors
- Temporary workarounds that need visibility
- High-priority learnings regardless of file location

**Adding Manual Memories** (Web Interface):
1. Open the module in **Edit Mode**
2. Scroll to **Manual Memories** section
3. Click **Add Memory** button (future feature)
4. Search for and select specific memories
5. Memories appear in the manual list
6. Can be removed individually with X button

**Manual vs. Automatic**:
- **Automatic** (via selectors): Dynamic, updates as memories change
- **Manual**: Static, requires explicit updates

## Composing Multiple Modules

Combine multiple modules to create rich, multi-faceted context packs.

### Module Priority

Priority (0-100) determines the order modules are processed:
- **Higher priority** (e.g., 90): Processed first, memories included early
- **Lower priority** (e.g., 10): Processed last, fills remaining budget

**Priority Strategy**:
```
Priority 90-100: Critical, must-have memories
Priority 70-89:  Important domain-specific context
Priority 40-69:  Standard workflow memories
Priority 10-39:  Nice-to-have, supplemental context
Priority 0-9:    Experimental or low-priority items
```

### Composition Example: Full-Stack Development

Create a suite of modules for different aspects of development.

**Module Suite**:
```
1. Architecture Decisions (Priority: 95)
   Types: [Decision]
   Min Confidence: 0.90
   Purpose: Core architectural decisions always included

2. API Development (Priority: 80)
   Types: [Decision, Constraint]
   Patterns: ["src/api/**"]
   Min Confidence: 0.75
   Purpose: Backend-specific context

3. Frontend Patterns (Priority: 80)
   Types: [Decision, Style Rule]
   Patterns: ["src/components/**", "*.tsx"]
   Min Confidence: 0.75
   Purpose: Frontend-specific context

4. Common Gotchas (Priority: 50)
   Types: [Gotcha]
   Min Confidence: 0.65
   Purpose: Known issues and workarounds

5. Experimental Learnings (Priority: 20)
   Types: [Learning]
   Min Confidence: 0.50
   Purpose: Recent discoveries and experiments
```

**Composition Behavior**:
When generating a pack with all 5 modules:
1. Architecture Decisions loads first (priority 95)
2. API Development and Frontend Patterns load next (priority 80)
3. Common Gotchas fills middle budget (priority 50)
4. Experimental Learnings fills remaining budget (priority 20)
5. If budget exhausted, lower priority modules are truncated

### Workflow-Specific Compositions

Create different module sets for different workflows.

**Debugging Session**:
```
Modules:
  - Common Gotchas (priority 90)
  - Error Patterns (priority 85)
  - Architecture Decisions (priority 50)

Budget: 4,000 tokens
Focus: Known issues and error solutions
```

**Code Review Session**:
```
Modules:
  - Style Rules (priority 90)
  - Architecture Decisions (priority 85)
  - Best Practices (priority 70)

Budget: 6,000 tokens
Focus: Coding standards and design patterns
```

**Feature Implementation**:
```
Modules:
  - Architecture Decisions (priority 95)
  - API Development (priority 80) OR Frontend Patterns (priority 80)
  - Common Gotchas (priority 60)
  - Recent Learnings (priority 30)

Budget: 8,000 tokens
Focus: Comprehensive development context
```

## Previewing Effective Context

Before generating a full context pack, preview what will be included and how the token budget is utilized.

### Understanding the Preview

The preview shows:
- **Items Included**: Number of memories selected
- **Items Available**: Total memories matching criteria
- **Total Tokens**: Estimated token count of selected memories
- **Budget**: Token limit configured
- **Utilization**: Percentage of budget used

**Utilization Tiers**:
- **Normal** (< 70%): Green - Good budget utilization
- **Warning** (70-90%): Yellow - Approaching limit
- **Critical** (> 90%): Red - Near or at budget limit

### Previewing via Web Interface

**Step 1: Open Context Pack Generator**
1. Navigate to **Memory** → **Context Modules** tab
2. Click **Generate Pack** button (or preview icon on a module card)

**Step 2: Configure Generation**
1. **Select Module**: Choose "All Modules" or specific module
2. **Set Budget**: Choose preset (1K, 2K, 4K, 8K, 16K) or enter custom
3. **Optional Filters**:
   - Filter by additional memory types
   - Increase minimum confidence threshold

**Step 3: Preview Results**
1. Click **Preview** button
2. View preview summary:
   ```
   Items Included: 23 / 45 available
   Total Tokens: 3,247 / 4,000 (81%)
   Utilization: Warning (approaching limit)
   ```
3. See breakdown by memory type:
   ```
   Decisions: 8 items (1,200 tokens)
   Constraints: 7 items (980 tokens)
   Gotchas: 5 items (720 tokens)
   Style Rules: 3 items (347 tokens)
   ```

**Step 4: Adjust if Needed**
- **Over budget** (> 100%): Increase budget or raise min confidence
- **Under budget** (< 50%): Lower min confidence or add more modules
- **Just right** (70-90%): Good utilization, ready to generate

### Previewing via CLI (Future Feature)

```bash
# Preview pack for all modules
skillmeat memory pack preview \
  --project my-project \
  --budget 4000

# Preview specific module
skillmeat memory pack preview \
  --project my-project \
  --module api-development \
  --budget 4000

# Preview with filters
skillmeat memory pack preview \
  --project my-project \
  --module api-development \
  --budget 4000 \
  --types decision,constraint \
  --min-confidence 0.80

# Output:
# Context Pack Preview
# ════════════════════
# Modules: api-development
# Budget: 4,000 tokens
#
# Items Included: 18 / 32 available
# Total Tokens: 3,156 / 4,000 (79%)
# Utilization: Warning
#
# Breakdown by Type:
#   Decisions:    9 items (1,520 tokens)
#   Constraints:  9 items (1,636 tokens)
#
# Ready to generate? Run:
#   skillmeat memory pack generate --project my-project --module api-development
```

## Generating Context Packs

Once satisfied with the preview, generate the full context pack with formatted markdown output.

### Pack Structure

Generated packs are structured markdown documents grouped by memory type:

```markdown
# Context Pack

## Decisions

- [high confidence] Use FastAPI for all REST endpoints (decision from 2026-01-15)
- [high confidence] Prefer Pydantic V2 for schema validation
- API responses must include request_id for tracing

## Constraints

- [medium confidence] Database connections limited to 50 concurrent
- All endpoints must complete within 2 seconds
- [high confidence] File uploads capped at 10MB

## Gotchas

- [medium confidence] SQLAlchemy sessions must be explicitly closed
- Authentication tokens expire after 24 hours - refresh mechanism required
- CORS must be configured for development and production separately

## Style Rules

- [high confidence] Use Black formatter with 100-character line length
- All public functions require docstrings
- Prefer explicit type hints over implicit
```

**Confidence Labels**:
- No label = High confidence (≥ 85%)
- `[medium confidence]` = Medium (60-84%)
- `[low confidence]` = Low (< 60%)

### Generating via Web Interface

**Step 1: Configure and Preview**
1. Follow preview steps (see Previewing Effective Context)
2. Verify preview results look correct
3. Confirm token utilization is acceptable

**Step 2: Generate Pack**
1. Click **Generate Pack** button
2. Wait for generation to complete (typically < 1 second)
3. Pack opens in preview modal

**Step 3: View Generated Pack**
The **Effective Context Preview** modal shows:
- **Header**: Token utilization bar with statistics
- **Item Summary**: Collapsible section showing all included memories
  - Grouped by type
  - Shows confidence percentage for each
- **Generated Markdown**: Full formatted pack ready to copy

**Step 4: Use the Pack**
Three options:
1. **Copy to Clipboard**: Click copy button, paste into agent context
2. **Export as File**: Download as `.md` file for archival
3. **Regenerate**: Make adjustments and regenerate

### Generating via CLI (Future Feature)

```bash
# Generate pack for specific module
skillmeat memory pack generate \
  --project my-project \
  --module api-development \
  --budget 4000

# Generate pack for all modules
skillmeat memory pack generate \
  --project my-project \
  --budget 8000

# Generate and save to file
skillmeat memory pack generate \
  --project my-project \
  --module api-development \
  --budget 4000 \
  --output context-pack.md

# Generate and copy to clipboard
skillmeat memory pack generate \
  --project my-project \
  --module api-development \
  --budget 4000 \
  --copy

# Output:
# Generated Context Pack
# ═══════════════════════
# Modules: api-development
# Items Included: 18
# Total Tokens: 3,156 / 4,000 (79%)
#
# ✓ Copied to clipboard
# ✓ Saved to: ~/.skillmeat/context-packs/api-development-2026-02-06.md
```

## Exporting and Copying Context Packs

### Copy to Clipboard

**Web Interface**:
1. Generate pack in Effective Context Preview modal
2. Click **Copy to Clipboard** button (top right)
3. Confirmation message appears
4. Paste into your agent context or documentation

**CLI** (Future Feature):
```bash
# Generate and copy in one command
skillmeat memory pack generate \
  --project my-project \
  --module api-development \
  --copy
```

### Export as Markdown File

Save generated packs for archival, sharing, or offline review.

**Web Interface**:
1. Generate pack in Effective Context Preview modal
2. Click **Export** dropdown
3. Choose **Download as Markdown**
4. File saved to downloads folder: `context-pack-api-development-2026-02-06.md`

**CLI** (Future Feature):
```bash
# Export to specific file
skillmeat memory pack generate \
  --project my-project \
  --module api-development \
  --output ~/Documents/api-context.md

# Export to default location
skillmeat memory pack generate \
  --project my-project \
  --module api-development \
  --export

# Default location: ~/.skillmeat/context-packs/[module]-[date].md
```

### Sharing Context Packs

**Use Cases**:
- Share with team members for code review
- Include in project documentation
- Archive as historical context snapshots
- Import into other projects

**Sharing Methods**:
1. **Email/Slack**: Copy to clipboard, paste into message
2. **Git Repository**: Export to file, commit to `.docs/context/`
3. **Team Wiki**: Export and upload to wiki/knowledge base
4. **Project Template**: Include in project scaffolding

## Managing Modules

### Editing Existing Modules

Update module configuration as your project evolves.

**Web Interface**:
1. Navigate to **Memory** → **Context Modules** tab
2. Find the module in the list
3. Click **Edit** button (pencil icon, appears on hover)
4. Modify fields:
   - Name, description, priority
   - Any selector configuration
   - Manual memory list (add/remove)
5. Click **Save Changes**

**CLI** (Future Feature):
```bash
# Update module name and description
skillmeat memory module update api-development \
  --name "API & Schema Development" \
  --description "Backend API and schema patterns"

# Update selectors
skillmeat memory module update api-development \
  --add-type decision \
  --remove-pattern "old/path/**" \
  --add-pattern "new/path/**" \
  --min-confidence 0.80

# Update priority
skillmeat memory module update api-development \
  --priority 90
```

### Deleting Modules

Remove modules that are no longer needed.

**Web Interface**:
1. Navigate to **Memory** → **Context Modules** tab
2. Find the module in the list
3. Click **Delete** button (trash icon, appears on hover)
4. Confirm deletion in dialog
5. Module is permanently removed

**Important**: Deleting a module does NOT delete the memories it references. Only the module configuration is removed.

**CLI** (Future Feature):
```bash
# Delete module
skillmeat memory module delete api-development

# Delete with confirmation skip
skillmeat memory module delete api-development --force

# Output:
# ⚠ Warning: This will permanently delete the module "API Development"
# Memories referenced by this module will NOT be deleted.
# Continue? [y/N]: y
# ✓ Module deleted: api-development
```

### Reordering Modules by Priority

Change module processing order by adjusting priorities.

**Strategy**:
1. **Identify Critical Modules**: What must always be included? (90-100)
2. **Domain-Specific Modules**: Important for specific workflows (70-89)
3. **Supplemental Modules**: Nice to have, budget permitting (40-69)
4. **Experimental Modules**: Low priority fill (0-39)

**Example Reorganization**:
```
Before:
  Architecture Decisions: 50
  API Development: 50
  Common Gotchas: 50
  Style Rules: 50

After:
  Architecture Decisions: 95 (critical, always first)
  API Development: 80 (important for backend work)
  Style Rules: 60 (standard reference)
  Common Gotchas: 40 (supplemental if budget allows)
```

**Web Interface**:
Edit each module and update priority field.

**CLI** (Future Feature):
```bash
# Update multiple priorities
skillmeat memory module update architecture-decisions --priority 95
skillmeat memory module update api-development --priority 80
skillmeat memory module update style-rules --priority 60
skillmeat memory module update common-gotchas --priority 40
```

### Duplicating Modules

Create a copy of an existing module as a starting point.

**Web Interface** (Future Feature):
1. Find the module to duplicate
2. Click **Duplicate** button
3. New module created with name "[Original Name] (Copy)"
4. Edit the copy to customize

**CLI** (Future Feature):
```bash
# Duplicate module
skillmeat memory module duplicate api-development \
  --new-name "Schema Development"

# Duplicate and modify
skillmeat memory module duplicate api-development \
  --new-name "Schema Development" \
  --remove-pattern "src/api/**" \
  --add-pattern "src/schemas/**"
```

## Token Budgeting

### Understanding Token Budgets

Token budgets limit the size of generated context packs to fit within AI model context windows.

**Common Budget Sizes**:
- **1,000 tokens** (~750 words): Small, focused context for specific tasks
- **2,000 tokens** (~1,500 words): Standard single-module context
- **4,000 tokens** (~3,000 words): Default, balanced context (recommended)
- **8,000 tokens** (~6,000 words): Large, multi-module context
- **16,000 tokens** (~12,000 words): Maximum, comprehensive context

**How Budgets Affect Selection**:
1. Modules processed by priority (highest first)
2. Within each module, memories selected by confidence (highest first)
3. Selection continues until budget exhausted
4. Remaining memories excluded

### Setting Budget Limits

**Web Interface**:
1. Open **Context Pack Generator**
2. **Budget** field shows preset buttons and custom input
3. Click preset: **1K**, **2K**, **4K**, **8K**, **16K**
4. Or enter custom value: `5000`
5. Preview updates to show estimated utilization

**CLI** (Future Feature):
```bash
# Use preset budget
skillmeat memory pack generate \
  --project my-project \
  --budget 4000

# Use custom budget
skillmeat memory pack generate \
  --project my-project \
  --budget 5500
```

### Budget Utilization Strategies

**Strategy 1: Fill Budget (Recommended)**
- Target: 70-90% utilization
- Ensures comprehensive context without waste
- Adjust module priorities or confidence thresholds to hit target

**Strategy 2: Under Budget**
- Target: 50-70% utilization
- Leaves room for ad-hoc context additions
- Good for workflows with unpredictable context needs

**Strategy 3: Strict Budget**
- Target: 90-100% utilization
- Maximizes information density
- Risk: May truncate important low-priority memories

**Example Adjustments**:
```
Problem: 45% utilization (under budget)
Solutions:
  - Lower min_confidence selector (0.75 → 0.65)
  - Add more module types
  - Include lower-priority modules

Problem: 105% utilization (over budget)
Solutions:
  - Raise min_confidence selector (0.70 → 0.80)
  - Reduce number of memory types
  - Increase budget limit
  - Remove lower-priority modules
```

### Budget Allocation Across Modules

When composing multiple modules, budget allocation follows priority order.

**Example: Three-Module Composition**
```
Budget: 4,000 tokens

Module 1: Architecture Decisions (Priority 95)
  - Selects memories until ~1,200 tokens used
  - Remaining budget: 2,800 tokens

Module 2: API Development (Priority 80)
  - Selects memories until ~1,500 tokens used
  - Remaining budget: 1,300 tokens

Module 3: Common Gotchas (Priority 50)
  - Selects memories until ~1,300 tokens used
  - Remaining budget: 0 tokens

Result:
  - Module 1: 1,200 tokens (30%)
  - Module 2: 1,500 tokens (37.5%)
  - Module 3: 1,300 tokens (32.5%)
  - Total: 4,000 tokens (100%)
```

**Uneven Allocation**:
If a high-priority module exhausts the budget:
```
Budget: 4,000 tokens

Module 1: All Memories (Priority 100, no filters)
  - Selects memories until 4,000 tokens used
  - Remaining budget: 0 tokens

Module 2: Never Processed
Module 3: Never Processed

Result: Only Module 1 included
```

**Tip**: Use selective filters and appropriate priorities to ensure balanced allocation.

## Best Practices

### Start Small, Iterate

Begin with simple modules and refine based on actual usage.

**Phase 1: Basic Modules**
```
Create:
  - Architecture Decisions (types: decision, min_confidence: 0.85)
  - Common Gotchas (types: gotcha, min_confidence: 0.70)
  - Style Rules (types: style_rule, min_confidence: 0.80)

Test:
  - Generate packs for different workflows
  - Note what's missing or excessive
```

**Phase 2: Domain-Specific Modules**
```
Add:
  - Frontend Patterns (patterns: "src/components/**", types: decision,style_rule)
  - Backend API (patterns: "src/api/**", types: decision,constraint)
  - Testing Strategies (patterns: "**/*.test.ts", types: gotcha,learning)

Refine:
  - Adjust confidence thresholds based on quality
  - Update file patterns as project structure evolves
```

**Phase 3: Workflow-Optimized Modules**
```
Specialize:
  - Code Review Context (types: style_rule,decision, priority: 90)
  - Debugging Context (types: gotcha, stages: debugging, priority: 95)
  - Onboarding Context (types: decision,learning, min_confidence: 0.85)

Compose:
  - Combine modules for comprehensive workflows
  - Use priority to control what loads first
```

### Use Descriptive Names

Module names should clearly indicate purpose and scope.

**Good Names**:
- `API Development - Backend Only`
- `React Component Patterns`
- `Debugging - Known Issues`
- `Code Review Standards`
- `Architecture - Core Decisions`

**Poor Names**:
- `Module 1`
- `Test`
- `Memories`
- `Important Stuff`

### Document Module Purpose

Use the description field to explain when and why to use each module.

**Example Descriptions**:
```
Name: API Development
Description: Backend API patterns, constraints, and gotchas. Use when
implementing or reviewing API endpoints. Includes FastAPI conventions,
schema validation patterns, and known edge cases.

Name: Frontend - Component Dev
Description: React component design patterns and style rules. Use during
component implementation and code review. Focuses on component composition,
hooks usage, and accessibility standards.

Name: Debugging - Database
Description: Database-related gotchas and fixes. Use when investigating
database connection issues, query performance problems, or ORM behavior.
Includes SQLAlchemy quirks and connection pool management.
```

### Regular Review and Updates

Modules should evolve with your project.

**Monthly Review Checklist**:
- [ ] Are selector criteria still relevant?
- [ ] Have new file paths been added to the project?
- [ ] Should min_confidence be adjusted based on memory quality?
- [ ] Are there new workflow stages to include?
- [ ] Should module priorities be reordered?
- [ ] Are there obsolete modules that should be deleted?

**Triggers for Updates**:
- Project structure refactoring
- New technology adoption (new framework, library)
- Team coding standards change
- Discovery of important memory gaps
- Excessive or insufficient token utilization

### Separate Concerns by Module

Create focused modules rather than catch-all configurations.

**Anti-Pattern: One Giant Module**
```
Name: Everything
Types: [all types]
Patterns: ["**/*"]
Min Confidence: 0.0
Priority: 50

Problem:
  - No prioritization of critical vs. nice-to-have
  - Can't compose for specific workflows
  - Token budget used inefficiently
```

**Better: Specialized Modules**
```
Module 1: Critical Architecture
  Types: [Decision]
  Min Confidence: 0.90
  Priority: 95

Module 2: Frontend Development
  Types: [Decision, Style Rule, Gotcha]
  Patterns: ["src/components/**", "*.tsx"]
  Min Confidence: 0.75
  Priority: 80

Module 3: Backend Development
  Types: [Decision, Constraint, Gotcha]
  Patterns: ["src/api/**", "*.py"]
  Min Confidence: 0.75
  Priority: 80

Module 4: Supplemental Learnings
  Types: [Learning]
  Min Confidence: 0.60
  Priority: 40

Benefits:
  - Compose different sets for different workflows
  - Clear prioritization of critical context
  - Efficient token budget usage
```

### Version Context Packs

Save generated packs with timestamps for historical reference.

**Naming Convention**:
```
context-pack-[module]-[date].md

Examples:
  context-pack-api-development-2026-02-06.md
  context-pack-debugging-2026-02-15.md
  context-pack-code-review-2026-02-20.md
```

**Use Cases**:
- Compare context evolution over time
- Audit what context was available during specific development
- Share snapshots with team for review
- Archive for compliance or documentation

## Troubleshooting

### Question: Preview shows 0 items included

**Symptom**: Preview returns "Items Included: 0 / 45 available"

**Possible Causes**:
1. **Selectors too restrictive**: Confidence threshold too high or type filters too narrow
2. **File patterns don't match**: Patterns don't match actual file paths in memories
3. **No memories match all criteria**: AND logic requires matching ALL selectors

**Solutions**:
```bash
# Check 1: Lower minimum confidence
Change: Min Confidence 0.90 → 0.70

# Check 2: Broaden memory types
Change: Types [Decision] → [Decision, Constraint, Learning]

# Check 3: Verify file patterns
Remove file patterns temporarily to test
If items appear, patterns are the issue

# Check 4: View available memories
Navigate to Memory Inbox → verify memories exist with expected types
```

### Question: Token utilization is too high (> 100%)

**Symptom**: Preview shows "Items Included: 35 / 40, Utilization: 127%"

**Causes**: Module selectors include too many memories for the budget.

**Solutions**:
```
Option 1: Increase budget
  Change: 4,000 tokens → 6,000 tokens
  Pro: Includes all desired memories
  Con: Larger context for AI to process

Option 2: Raise confidence threshold
  Change: Min Confidence 0.70 → 0.85
  Pro: Higher quality memories only
  Con: May exclude useful medium-confidence items

Option 3: Narrow memory types
  Change: Types [Decision, Constraint, Gotcha, Learning] → [Decision, Constraint]
  Pro: More focused context
  Con: Loses supplemental information

Option 4: Add file pattern filter
  Add: Patterns ["src/api/**"] (if module is too broad)
  Pro: Domain-specific focus
  Con: Excludes memories from other areas
```

### Question: Token utilization is too low (< 50%)

**Symptom**: Preview shows "Items Included: 8 / 30, Utilization: 32%"

**Causes**: Module selectors are too restrictive or not enough memories exist.

**Solutions**:
```
Option 1: Lower confidence threshold
  Change: Min Confidence 0.85 → 0.65
  Pro: Includes more memories
  Con: Some lower-quality items may appear

Option 2: Broaden memory types
  Change: Types [Decision] → [Decision, Constraint, Learning]
  Pro: More diverse context
  Con: May dilute focus

Option 3: Remove file pattern restrictions
  Change: Remove patterns entirely or broaden them
  Pro: Includes memories from all areas
  Con: May include irrelevant domain memories

Option 4: Add more memories
  Navigate to Memory Inbox → approve candidate memories
  Pro: Enriches knowledge base
  Con: Requires manual triage effort
```

### Question: Generated pack includes irrelevant memories

**Symptom**: Context pack contains memories unrelated to intended workflow.

**Causes**: Selectors too broad or priorities misconfigured.

**Solutions**:
```
Step 1: Review selector configuration
  - Are file patterns specific enough?
  - Is minimum confidence appropriate?
  - Are memory types correctly selected?

Step 2: Use manual exclusion (future feature)
  - Explicitly exclude specific memories from module

Step 3: Create more focused module
  Instead of: "General Development"
  Create: "API Development" + "Frontend Development" as separate modules

Step 4: Adjust priorities
  - Lower priority of overly broad modules
  - Higher priority of focused modules
```

### Question: Module not appearing in generation

**Symptom**: Multiple modules exist, but one doesn't contribute to generated pack.

**Causes**: Module priority too low or budget exhausted before reaching it.

**Diagnostic**:
```
Check priority order:
  Module A: Priority 90 ✓ Included
  Module B: Priority 80 ✓ Included
  Module C: Priority 50 ✗ Not Included (budget exhausted)

Budget: 4,000 tokens
Module A used: 2,000 tokens
Module B used: 2,000 tokens
Remaining: 0 tokens → Module C skipped
```

**Solutions**:
```
Option 1: Increase budget
  4,000 tokens → 6,000 tokens

Option 2: Raise module priority
  Module C: Priority 50 → 85
  May get processed before Module B

Option 3: Make higher-priority modules more selective
  Module A: Add min_confidence 0.85 (reduces selection)
  Module B: Narrow file patterns
  Leaves budget for Module C
```

### Question: How to create module for specific workflow?

**Scenario**: Need a module for "API endpoint implementation" workflow.

**Process**:
```
Step 1: Identify needed information
  - API design patterns and decisions
  - Schema validation constraints
  - Known endpoint gotchas
  - FastAPI conventions

Step 2: Determine selector criteria
  Memory Types: [Decision, Constraint, Gotcha]
  File Patterns: ["src/api/**", "src/schemas/**"]
  Min Confidence: 0.75 (balance quality and coverage)
  Workflow Stages: [implementation]

Step 3: Create module
  Name: API Endpoint Implementation
  Description: Context for implementing FastAPI endpoints
  Priority: 85 (high, but not critical)
  Selectors: (as above)

Step 4: Test and refine
  Generate preview → check utilization
  Generate full pack → review content quality
  Adjust selectors based on results
```

## See Also

- **[Memory & Context Intelligence Guide](/docs/user/guides/memory-context-system.md)** - System overview and workflow map
- **[Memory Inbox User Guide](/docs/user/guides/memory-inbox.md)** - Memory triage and lifecycle operations
- **[Web UI Guide](/docs/user/guides/web-ui-guide.md)** - Complete web interface documentation
- **[CLI Commands Reference](/docs/user/cli/commands.md)** - Command-line interface for memory and modules
- **[PRD: Memory & Context Intelligence System](/docs/project_plans/PRDs/features/memory-context-system-v1.md)** - Technical specification and architecture
