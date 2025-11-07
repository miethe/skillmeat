---
title: Claude Code Configuration Repository Operating Manual
description: Comprehensive guide for operating the MeatyPrompts Claude Code configuration repository containing 50 agents, 55 commands, utilities, and skills for comprehensive AI-assisted development
audience: [ai-agents, developers]
tags: [claude-code, configuration, agents, commands, operating-manual]
created: 2025-11-05
updated: 2025-11-05
category: configuration-deployment
status: published
related:
  - ./TEMPLATIZATION_GUIDE.md
  - ./README.md
  - ./examples/README.md
  - ./scripts/README.md
  - ./skills/symbols/SKILL.md
---

# Claude Code Configuration Repository — Operating Manual

This is a comprehensive Claude Code configuration repository containing 50+ specialized agents, 55+ commands, utility scripts, and reusable skills designed to orchestrate complete software development workflows for the MeatyPrompts project.

**Quick Links:**
- Getting started? See [Installation & Setup](#installation--setup)
- Need documentation? See [Repository Structure](#repository-structure)
- Adding new agents? See [Creating New Agents](#creating-new-agents)
- Customizing for your project? See [Customization Guide](#customization-for-your-project)

## Prime Directives

This repository contains a reusable Claude Code configuration system. When working in this repo, follow these core principles:

### 1. Follow Existing Patterns and Conventions

- **Agent Format**: All agents use YAML frontmatter with metadata (name, description, category, tools, color, model)
- **Command Format**: All commands use YAML frontmatter with metadata (description, tools, argument hints)
- **Script Format**: All scripts follow consistent function naming (verb_noun) with comprehensive error handling
- **Directory Organization**: Group agents and commands by category (ai/, architects/, dev-team/, etc.)
- When creating new agents, commands, or scripts, mirror the structure and style of existing ones in the same category

### 2. Test All Agents and Commands Before Committing

- Test new agents with `Task("agent-name", "test task description")`
- Test new commands with `/command-name arg1 arg2`
- Verify YAML frontmatter is valid (no syntax errors)
- Ensure agent prompt is clear and actionable
- Check that all referenced tools are in the `tools` list

### 3. Document All Customization Points

- Mark project-specific values with `{{VARIABLE_NAME}}` format
- Add explanatory comments for non-obvious logic
- Document when fields are required vs. optional
- Include examples in agent descriptions
- Keep documentation up-to-date when changing behavior

### 4. Maintain Backward Compatibility

- Don't remove or rename agents/commands without updating references
- If changing agent behavior, check all places it's invoked
- Update subagents.json when changing tool invocations
- Document breaking changes in commit messages
- Support both old and new patterns during transition periods

### 5. Reuse and Adapt Before Building New

- Before creating a new agent, check existing agents in similar categories
- Check if an existing command can be adapted before creating a new one
- Use utility scripts from scripts/ directory rather than duplicating functionality
- Create new agents only when no existing agent serves the purpose
- Prefix new agent names clearly (e.g., `lead-architect` for senior role)

## Repository Structure

```
claude-export/
├── agents/                          # 50 specialized agents (9 categories)
│   ├── ai/                          # AI experts (exploration, symbols, codebase)
│   │   ├── codebase-explorer.md     # Fast codebase pattern discovery
│   │   ├── explore.md               # Deep codebase analysis
│   │   └── ...
│   │
│   ├── architects/                  # Architecture experts
│   │   ├── lead-architect.md        # Senior system architect
│   │   ├── backend-architect.md     # Backend/API patterns
│   │   ├── nextjs-architecture-expert.md
│   │   ├── data-layer-expert.md     # Database and persistence
│   │   └── ...
│   │
│   ├── dev-team/                    # Implementation engineers
│   │   ├── backend-engineer.md      # Backend implementation
│   │   ├── python-backend-engineer.md # Python expert
│   │   ├── frontend-developer.md    # Frontend/React expert
│   │   ├── mobile-app-builder.md    # React Native/Expo expert
│   │   ├── ui-engineer-enhanced.md  # UI component expert
│   │   └── ...
│   │
│   ├── fix-team/                    # Debugging & refactoring specialists
│   │   ├── ultrathink-debugger.md   # Deep debugging with extended thinking
│   │   ├── refactoring-expert.md    # Code refactoring specialist
│   │   └── ...
│   │
│   ├── pm/                          # Product management orchestration
│   │   ├── lead-pm.md               # SDLC orchestrator
│   │   ├── prd-writer.md            # Product requirements documents
│   │   ├── implementation-planner.md # Detailed task breakdown
│   │   ├── feature-planner.md       # Feature analysis
│   │   ├── spike-writer.md          # Research spikes
│   │   ├── task-decomposition-expert.md
│   │   └── ...
│   │
│   ├── reviewers/                   # Quality assurance specialists
│   │   ├── code-reviewer.md         # Peer code review
│   │   ├── senior-code-reviewer.md  # Senior code review
│   │   ├── task-completion-validator.md # Task validation
│   │   ├── api-librarian.md         # API review
│   │   ├── telemetry-auditor.md     # Observability review
│   │   ├── karen.md                 # Strict QA enforcement
│   │   └── ...
│   │
│   ├── tech-writers/                # Documentation specialists
│   │   ├── documentation-writer.md  # 90% of docs (Haiku optimized)
│   │   ├── documentation-complex.md # Complex multi-system docs
│   │   ├── documentation-planner.md # Documentation strategy planning
│   │   ├── api-documenter.md        # API documentation
│   │   ├── technical-writer.md      # Technical documentation
│   │   ├── openapi-expert.md        # OpenAPI/Swagger specs
│   │   ├── changelog-generator.md   # Version history docs
│   │   └── ...
│   │
│   ├── ui-ux/                       # Design system experts
│   │   ├── ui-designer.md           # UI/design expert
│   │   ├── ux-researcher.md         # UX research specialist
│   │   └── ...
│   │
│   └── web-optimize-team/           # Performance & accessibility
│       ├── react-performance-optimizer.md # React performance tuning
│       ├── web-accessibility-checker.md   # WCAG compliance
│       ├── url-context-validator.md       # URL validation
│       └── url-link-extractor.md          # Link extraction
│
├── commands/                        # 55 slash commands (11 categories)
│   ├── ai/                          # Symbol operations
│   │   ├── symbols-query.md         # Query symbols efficiently
│   │   ├── symbols-search.md        # Search symbol system
│   │   ├── symbols-update.md        # Regenerate symbols
│   │   ├── symbols-chunk.md         # Load symbol chunks
│   │   └── load-symbols.md          # Initialize symbol system
│   │
│   ├── analyze/                     # Codebase analysis
│   │   ├── analyze-architecture.md  # Architecture compliance checks
│   │   ├── codebase-audit.md        # Full codebase audit
│   │   └── ...
│   │
│   ├── artifacts/                   # Generate/update artifacts
│   │   ├── update-symbols.md        # Update symbol graph
│   │   ├── update-docs.md           # Documentation updates
│   │   ├── update-contracts.md      # API contract updates
│   │   └── ...
│   │
│   ├── dev/                         # Feature development
│   │   ├── create-feature.md        # New feature setup
│   │   ├── implement-story.md       # Story implementation
│   │   ├── add-endpoint.md          # New API endpoint
│   │   └── ...
│   │
│   ├── fix/                         # Bug fixes
│   │   ├── bugfix-commit.md         # Create bug fix commit
│   │   ├── violation-fix.md         # Fix architecture violations
│   │   └── ...
│   │
│   ├── integrations/                # External tool integration
│   │   ├── linear-create-issue.md   # Create Linear issue
│   │   ├── github-pr-create.md      # Create GitHub PR
│   │   ├── trello-add-card.md       # Add Trello card
│   │   └── ...
│   │
│   ├── plan/                        # Planning operations
│   │   ├── design-system.md         # Design system work
│   │   ├── plan-refactor.md         # Refactoring planning
│   │   ├── spike-research.md        # Research spike
│   │   └── ...
│   │
│   ├── pm/                          # Product management
│   │   ├── write-prd.md             # Write PRD
│   │   ├── create-implementation-plan.md # Implementation plan
│   │   ├── validate-task.md         # Task validation
│   │   └── ...
│   │
│   ├── review/                      # Code review
│   │   ├── review-code.md           # Code review
│   │   ├── review-architecture.md   # Architecture review
│   │   ├── review-story.md          # Story review
│   │   └── ...
│   │
│   ├── stubs/                       # Quick stubs/templates
│   │   └── ...
│   │
│   └── [Category-specific commands]
│       ├── memory-spring-cleaning.md # Clear context cache
│       ├── router-migrate.md        # Router migration
│       ├── session-learning-capture.md # Session notes
│       └── ...
│
├── scripts/                         # 12 utility scripts
│   ├── architecture-utils.sh        # Architecture checking utilities
│   ├── artifact-utils.sh            # Artifact generation utilities
│   ├── backup-utils.sh              # Backup and recovery utilities
│   ├── ci-utils.sh                  # CI/CD pipeline utilities
│   ├── contract-utils.sh            # API contract utilities
│   ├── file-utils.sh                # File operation utilities
│   ├── git-utils.sh                 # Git workflow utilities
│   ├── json-utils.sh                # JSON parsing utilities
│   ├── report-utils.sh              # Report generation utilities
│   ├── story-helpers.sh             # Story/task utilities
│   ├── validation-utils.sh          # Validation and checks
│   ├── README.md                    # Script documentation
│   └── [Custom project scripts]
│
├── hooks/                           # Git and shell hooks
│   ├── pre-commit.sh                # Pre-commit checks
│   ├── post-commit.sh               # Post-commit actions
│   └── ...
│
├── skills/                          # Reusable custom skills
│   ├── symbols/                     # Symbol system (codebase indexing)
│   │   ├── SKILL.md                 # Comprehensive skill documentation
│   │   ├── README.md                # Quick reference
│   │   ├── symbols.config.json      # Configuration
│   │   ├── symbols-config-schema.json # Configuration schema
│   │   ├── scripts/                 # Symbol generation scripts
│   │   └── templates/               # Symbol templates
│   │
│   ├── skill-creator/               # Skill creation utilities
│   │   ├── SKILL.md                 # Skill documentation
│   │   └── templates/               # Creation templates
│   │
│   └── [Custom project skills]
│
├── templates/                       # Reusable templates
│   ├── pm/                          # PM templates
│   │   ├── prd-template.md          # PRD template
│   │   ├── implementation-plan-template.md # Implementation plan template
│   │   ├── spike-template.md        # Spike research template
│   │   └── ...
│   │
│   ├── technical/                   # Technical templates
│   │   ├── adr-template.md          # Architecture Decision Record
│   │   ├── api-spec-template.md     # API specification
│   │   └── ...
│   │
│   └── [Custom project templates]
│
├── config/                          # Configuration files
│   ├── subagents.json               # Agent invocation rules
│   ├── [Project-specific configs]
│   └── ...
│
├── examples/                        # MeatyPrompts-specific examples
│   ├── README.md                    # Examples documentation
│   ├── plans/                       # Example implementation plans
│   ├── progress/                    # Example progress tracking
│   ├── worknotes/                   # Example worknotes/context
│   ├── analysis/                    # Example bug analysis
│   └── summary/                     # Example summaries
│
├── other/                           # Legacy/miscellaneous
│   ├── symbols/                     # Legacy symbol files
│   └── ...
│
├── settings.json                    # Claude Code settings & permissions
├── settings.local.json              # Local settings overrides (gitignored)
├── CLAUDE.md                        # This file — operating manual
├── TEMPLATIZATION_GUIDE.md          # Customization guide
├── README.md                        # Repository overview
└── .gitignore                       # Git ignore rules
```

## Installation & Setup

### Option 1: Direct Copy (Simplest)

Copy the `.claude/` contents from this repository to your project:

```bash
# Copy entire .claude directory to your project
cp -r claude-export/.claude /path/to/your/project/.claude

# Then customize for your project (see Customization section)
```

### Option 2: Git Submodule (Recommended for Updates)

Add as a git submodule to receive upstream updates:

```bash
# Add as submodule
git submodule add https://github.com/yourorg/claude-export .claude-config

# Copy to .claude directory
cp -r .claude-config/claude-export/* .claude/

# Then customize for your project
```

To update from upstream:

```bash
cd .claude-config && git pull origin main && cd ..
cp -r .claude-config/claude-export/* .claude/
```

### Option 3: Fork and Customize (Full Control)

Fork this repository and customize directly:

```bash
# Clone your fork
git clone https://github.com/yourorg/claude-export

# Customize all variables and paths
# See TEMPLATIZATION_GUIDE.md for details

# Copy customized version to .claude
cp -r your-fork/* .claude/
```

### Post-Installation Configuration

1. **Review settings.json** - Adjust permissions and hooks for your project
2. **Update subagents.json** - Configure agent invocation rules
3. **Configure project variables** - Replace `{{VARIABLES}}` (see Customization section)
4. **Test an agent** - Run `Task("codebase-explorer", "Find all components in src/")` to verify setup
5. **Review examples/** - Study examples for your specific project type

## Creating New Agents

### Step 1: Choose the Category

Place your agent in the appropriate directory:

- **`agents/ai/`** - Codebase exploration, symbol engineering, AI utilities
- **`agents/architects/`** - System architecture, domain experts
- **`agents/dev-team/`** - Implementation engineers (Python, TypeScript, Mobile, UI)
- **`agents/fix-team/`** - Debugging, refactoring, issue resolution
- **`agents/pm/`** - Product management, planning, SDLC orchestration
- **`agents/reviewers/`** - Code review, validation, quality assurance
- **`agents/tech-writers/`** - Documentation specialists
- **`agents/ui-ux/`** - Design system, UI/UX
- **`agents/web-optimize-team/`** - Performance, accessibility, optimization

### Step 2: Create Agent File with YAML Frontmatter

Create `agents/[category]/[agent-name].md`:

```yaml
---
name: agent-name
description: "Clear description of when to use this agent with 2-3 examples of use cases"
category: category-name
tools: [Read, Write, Edit, Bash, Grep, Glob, Task, WebSearch]
color: blue
model: sonnet
---

# Agent Title

## Core Mission

Clear, specific description of the agent's role and responsibilities.

## When to Use This Agent

- **Scenario 1**: Example of when this agent is useful
- **Scenario 2**: Another example
- **Scenario 3**: Clear differentiation from similar agents

## When NOT to Use This Agent

- When you need [different capability]
- Instead use [other agent name] when [condition]

## Key Expertise

- **Expertise Area 1**: Description
- **Expertise Area 2**: Description
- **Expertise Area 3**: Description

## Process & Workflow

[Detailed workflow and step-by-step processes]

## Tools & Resources

- **Tools Used**: [List of tools from frontmatter]
- **Key Commands**: [Related commands this agent typically invokes]
- **Related Agents**: [Other agents this agent typically delegates to]

## Examples

### Example 1: [Scenario]

[Example prompt and expected behavior]

### Example 2: [Scenario]

[Example prompt and expected behavior]

## Best Practices

- Practice 1 with explanation
- Practice 2 with explanation
- Practice 3 with explanation

## Limitations & Boundaries

- Limitation 1: What this agent cannot do
- Limitation 2: When to use a different agent instead
- Limitation 3: Known constraints

## Output Format

Clear description of what this agent outputs and how it's structured.
```

### Step 3: Test the Agent

```bash
# Test with a real task
Task("agent-name", "Your test task description")

# Verify:
# - Agent loads successfully
# - YAML frontmatter is valid
# - Agent understands its role
# - Output is clear and actionable
```

### Step 4: Document in README

Update relevant documentation to mention your new agent:

- Add to `agents/[category]/README.md` if it exists
- Add to main `README.md` if it's a major agent
- Add reference to related agents and when to use

### Agent Creation Checklist

- [ ] File created in appropriate category directory
- [ ] YAML frontmatter is valid and complete
- [ ] `name` field matches filename (kebab-case)
- [ ] `description` has 2-3 concrete examples
- [ ] All tools used are in `tools` list
- [ ] Agent prompt is clear and actionable
- [ ] "When to use" section is explicit
- [ ] "When NOT to use" section clarifies boundaries
- [ ] Examples show real-world scenarios
- [ ] Tested with `Task("agent-name", "test")`
- [ ] All references to related agents are documented

## Creating New Commands

### Step 1: Choose the Category

Place your command in the appropriate directory:

- **`commands/ai/`** - Symbol operations and AI utilities
- **`commands/analyze/`** - Codebase analysis and audits
- **`commands/artifacts/`** - Generate and update artifacts
- **`commands/dev/`** - Feature development operations
- **`commands/fix/`** - Bug fixes and issue resolution
- **`commands/integrations/`** - External tool integration
- **`commands/plan/`** - Planning and research operations
- **`commands/pm/`** - Product management operations
- **`commands/review/`** - Code and design review
- **`commands/stubs/`** - Quick templates and stubs

### Step 2: Create Command File with YAML Frontmatter

Create `commands/[category]/[command-name].md`:

```yaml
---
name: command:name
description: "Clear, concise description of what this command does"
argument-hint: "[required-arg] [optional-arg]"
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob, Task]
---

# Command Name

## Description

Clear explanation of what the command does and when to use it.

## Arguments

- `arg1` (required): Description of first argument
- `arg2` (optional): Description of second argument

## Options

- `--flag`: Description of what this flag does
- `--option=value`: Description with example values

## Usage Examples

### Basic Usage

```bash
/command-name argument value
```

### With Options

```bash
/command-name argument value --option=data
```

## Output

Description of what the command outputs and in what format.

## Related Commands

- `/related-command-1` - When to use instead
- `/related-command-2` - Related functionality
```

### Step 3: Test the Command

```bash
# Test the command
/command-name test-argument

# Verify:
# - Command executes successfully
# - YAML frontmatter is valid
# - Arguments are handled correctly
# - Output is clear and properly formatted
```

### Step 4: Document in README

Update `commands/README.md` and category-specific README files.

### Command Creation Checklist

- [ ] File created in appropriate category directory
- [ ] Filename matches command name (kebab-case with .md extension)
- [ ] YAML frontmatter is valid and complete
- [ ] `description` is clear and actionable
- [ ] `argument-hint` shows required vs optional clearly
- [ ] All tools used are in `allowed-tools` list
- [ ] Command implementation is clear and logical
- [ ] Usage examples cover common scenarios
- [ ] Output format is documented
- [ ] Tested with actual arguments
- [ ] Related commands are referenced

## Creating New Scripts

### Step 1: Add to scripts/ Directory

Create `scripts/[category]-utils.sh` or add to existing category file.

### Step 2: Follow Script Conventions

```bash
#!/bin/bash
# Brief description of script purpose
# Usage: source this file and call functions

# Function naming: verb_noun (e.g., check_architecture, validate_test)
# All functions should have error handling and clear output

# Document all functions
# function_name() {
#   Description of what this function does
#   Usage: function_name arg1 arg2
#   Returns: exit code and output
#   ...
# }

function_name() {
  local arg1="$1"
  local arg2="$2"

  # Validate inputs
  if [[ -z "$arg1" ]]; then
    echo "Error: arg1 is required" >&2
    return 1
  fi

  # Implementation with error handling
  if ! some_command "$arg1"; then
    echo "Error: operation failed" >&2
    return 1
  fi

  echo "Success: operation completed"
  return 0
}
```

### Step 3: Document Functions

Update `scripts/README.md` with:

- Function name and category
- Description of purpose
- Usage examples
- Return codes and output format
- Dependencies

### Script Guidelines

- **Naming**: Use `verb_noun` format (e.g., `validate_config`, `generate_report`)
- **Error Handling**: Check exit codes, validate inputs, provide clear error messages
- **Composability**: Make scripts callable from other scripts
- **Idempotency**: Scripts should be safe to run multiple times
- **Documentation**: Include header comment and function documentation
- **Testing**: Test with various inputs before committing

## Creating New Skills

### Step 1: Plan the Skill

Determine:
- **Purpose**: What problem does this skill solve?
- **Scope**: What functionality does it provide?
- **Dependencies**: What tools, libraries, or configurations are required?
- **Reusability**: Can this be used by other projects?

### Step 2: Create Skill Directory

Create `skills/[skill-name]/` with structure:

```
skills/[skill-name]/
├── SKILL.md                    # Comprehensive documentation
├── README.md                   # Quick reference
├── [skill-name].config.json    # Configuration schema
├── [skill-name]-schema.json    # Configuration schema validation
├── scripts/                    # Implementation scripts
│   ├── setup.sh               # Initialization
│   ├── generate.sh            # Generation logic
│   └── validate.sh            # Validation logic
├── templates/                 # Reusable templates
│   ├── config-template.json   # Example configuration
│   └── usage-template.md      # Usage template
└── examples/                  # Example outputs
    ├── example-1.json         # Example 1
    └── example-2.json         # Example 2
```

### Step 3: Document the Skill

Create comprehensive `SKILL.md`:

```markdown
# Skill Name

## Overview

Clear description of what this skill does and how it benefits the project.

## Purpose & Use Cases

- Use case 1 with explanation
- Use case 2 with explanation
- Use case 3 with explanation

## Prerequisites

- Requirement 1
- Requirement 2
- Requirement 3

## Installation

Step-by-step setup instructions.

## Configuration

Document all configuration options.

## Usage Patterns

Include practical examples of using the skill.

## API Reference

Document all functions, hooks, and interfaces.

## Examples

Complete working examples.

## Troubleshooting

Common issues and solutions.

## Maintenance

How to update, extend, or troubleshoot the skill.
```

### Step 4: Test the Skill

- Create test configuration
- Verify all functions work as documented
- Test error cases
- Document any edge cases

## Customization for Your Project

### Understanding Variables

This repository uses `{{VARIABLE_NAME}}` placeholders for project-specific values. See [TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md) for comprehensive variable documentation.

### Common Customizations

1. **Project Name & Domain** - Replace all instances of "MeatyPrompts" with your project name
2. **Architecture Pattern** - Update architecture descriptions to match your system
3. **Tool Integration** - Configure for your PM tool (Linear, Jira, GitHub, Trello, etc.)
4. **Standards & Patterns** - Update to match your project's conventions
5. **Documentation Policy** - Adapt documentation rules to your project
6. **Authentication** - Update auth method references (Clerk → Auth0, etc.)
7. **Observability** - Configure for your logging/tracing system

### Step-by-Step Customization

1. **Copy Repository**
   ```bash
   cp -r claude-export .claude
   ```

2. **Create Customization Config** (optional)
   ```json
   {
     "projectName": "YourProject",
     "projectDomain": "Your Business Domain",
     "pmTool": "Linear",
     "authMethod": "Auth0",
     "apiFramework": "FastAPI",
     "webFramework": "Next.js"
   }
   ```

3. **Replace Variables** - Use find & replace or a script:
   ```bash
   # Find all {{VARIABLES}} in a file
   grep -r '{{[A-Z_]*}}' .claude/

   # Replace specific variables
   find .claude -type f -name "*.md" | xargs sed -i 's/{{PROJECT_NAME}}/YourProject/g'
   ```

4. **Update Examples** - Customize `examples/` directory with your project's examples

5. **Configure Settings** - Update `settings.json` for your environment

6. **Test Configuration** - Run agents to verify customization worked

## Configuration Files

### settings.json

Controls permissions and hooks for Claude Code:

```json
{
  "permissions": {
    "deny": ["Read(./secrets/**)", "Bash(rm -rf:*)"],
    "ask": ["Bash(git push:*)", "Bash(docker:*)"],
    "allow": ["Read(./**)", "Write(./**)", "Edit"]
  },
  "hooks": {
    "PreToolUse": [],
    "PostToolUse": [],
    "SessionStart": []
  }
}
```

**Key Settings:**
- **deny**: Tools/patterns that are completely blocked
- **ask**: Operations that require confirmation
- **allow**: Operations that are always allowed
- **hooks**: Pre/post tool-use, session start/end hooks

See [Claude Code documentation](https://claudecode.anthropic.com/) for complete settings reference.

### settings.local.json

Local overrides of `settings.json` (gitignored). Use for:

- Local-only hooks
- Development-only permissions
- Personal settings

### config/subagents.json

Defines rules for agent invocation:

```json
{
  "rules": [
    {
      "when": "pattern_match",
      "agent": "recommended-agent",
      "confidence": 0.9
    }
  ]
}
```

Used by Claude Code to suggest appropriate agents for tasks.

### skills/symbols/symbols.config.json

Configuration for the symbol system:

```json
{
  "domains": {
    "ui": { "source": "src/components", "include": ["*.ts", "*.tsx"] },
    "api": { "source": "api/", "include": ["*.py"] }
  },
  "regenerateOnStart": false,
  "cacheEnabled": true
}
```

## Testing Your Changes

### Testing New Agents

```bash
# Test agent with a simple task
Task("new-agent-name", "Simple test task")

# Verify:
# ✓ Agent loads and responds
# ✓ Output is clear and actionable
# ✓ All referenced tools work
# ✓ No errors in frontmatter
```

### Testing New Commands

```bash
# Test command with arguments
/new-command-name test-arg1 test-arg2

# Verify:
# ✓ Command executes without errors
# ✓ Arguments are parsed correctly
# ✓ Output format is as documented
# ✓ Help text is clear
```

### Testing Scripts

```bash
# Source script and test functions
source scripts/category-utils.sh

# Test function with various inputs
function_name "test_arg"

# Verify:
# ✓ Function runs successfully
# ✓ Error handling works correctly
# ✓ Output is properly formatted
```

### Testing Skills

```bash
# Source skill
source skills/skill-name/scripts/setup.sh

# Run skill operations
skill_generate_command

# Verify:
# ✓ Configuration is valid
# ✓ Operations complete successfully
# ✓ Output matches documentation
```

## Common Patterns

### When to Create an Agent vs. a Command

| Aspect | Agent | Command |
|--------|-------|---------|
| **Complexity** | Complex multi-step workflows | Single focused operation |
| **Interaction** | Extended conversation/reasoning | Quick execution |
| **State** | Maintains context across turns | Stateless |
| **Delegation** | Delegates to other agents | Calls scripts/tools |
| **Use** | `Task("agent-name", "description")` | `/command-name args` |

**Examples:**
- Agent: "lead-pm" orchestrates entire SDLC
- Command: "/create-feature" sets up new feature structure

### Using Utility Scripts Effectively

1. **Source in Commands**: Import scripts at command top
   ```bash
   source ../scripts/git-utils.sh
   ```

2. **Use in Agents**: Call scripts for common operations
   ```bash
   Task("bash-command", "Call setup_git_config")
   ```

3. **Chain Functions**: Compose functions from multiple scripts
   ```bash
   validate_config && generate_artifact
   ```

### Symbol System for Token Efficiency

The symbol system provides metadata about codebase without loading entire files:

```bash
# Query symbols efficiently
/symbols:query --name="Component"

# Load specific domain
/load-symbols --domain=ui

# Update symbol index
/symbols:update
```

Reduces token usage by 95-99% compared to full file loading.

### Progress Tracking & Worknotes

Structure tracking documents following CLAUDE.md policies:

```
.claude/
├── progress/[prd-name]/
│   ├── phase-1-progress.md
│   └── phase-2-progress.md
├── worknotes/[prd-name]/
│   ├── phase-1-context.md
│   └── phase-2-context.md
└── worknotes/observations/
    └── observation-log-11-25.md
```

One file per phase, monthly observation logs.

### CRITICAL: Documentation vs AI Artifacts

**Before creating ANY content, determine: Is this for HUMANS or AI AGENTS?**

#### Documentation = For Humans

**Purpose:** Help humans understand, use, and maintain {{PROJECT_NAME}}
**Audience:** Developers, users, maintainers
**Location:** `/docs/`, README files, code comments

**Agents:** `documentation-writer`, `documentation-complex`, `documentation-planner`

**Examples:**
- API documentation for developers to understand endpoints
- Setup guides for users to install and configure
- README files explaining what packages do
- How-to guides for accomplishing tasks
- Architecture documentation explaining system design

#### AI Artifacts = For AI Agents

**Purpose:** Make AI agents more effective through context engineering
**Audience:** AI agents, Claude Code CLI, automation systems
**Location:** `.claude/`, `claude-export/`, `ai/`

**Agent:** `ai-artifacts-engineer`

**Examples:**
- Skills - Claude Code capabilities (`.claude/skills/`)
- Agent Prompts - Specialized subagents (`.claude/agents/`)
- Context Files - Progress tracking (`.claude/worknotes/`, `.claude/progress/`)
- Workflow Automation - Multi-agent orchestration
- Symbol Graphs - Token-optimized metadata (`ai/symbols-*.json`)
- Slash Commands - YAML frontmatter commands (`.claude/commands/`)

### Documentation Delegation (For Human Documentation)

**Delegate ALL human documentation work to specialized agents:**

| Documentation Type | Agent | Model | When to Use |
|-------------------|-------|-------|-------------|
| Most documentation (90%) | `documentation-writer` | Haiku 4.5 | READMEs, API docs, guides, comments, integration docs, component docs |
| Complex multi-system docs (5%) | `documentation-complex` | Sonnet | 5+ services, deep trade-offs, complex synthesis |
| Documentation planning (5%) | `documentation-planner` | Opus | Planning ONLY - analyzes what/how to document, then delegates writing |

**Examples:**

```markdown
# Most documentation - Haiku 4.5 (fast, capable, cheap)
Task("documentation-writer", "Create README for auth-utils module")
Task("documentation-writer", "Document authentication API with complete specifications")
Task("documentation-writer", "Document all Button component variants with accessibility notes")

# Complex multi-system docs - Sonnet (rare use)
Task("documentation-complex", "Document integration between 5+ microservices with all data flows and error scenarios")

# Documentation planning - Opus (planning only, not writing)
Task("documentation-planner", "Analyze what docs are needed for authentication system and create plan")
→ Planner analyzes with Opus
→ Planner delegates writing to documentation-writer (Haiku)
```

**Key Insight:** Haiku 4.5 handles 90% of documentation excellently. Only use Sonnet for genuinely complex docs. Use Opus only for planning (never writing).

### AI Artifacts Delegation (For AI Agent Consumption)

**Delegate ALL AI artifact creation to ai-artifacts-engineer:**

| AI Artifact Type | Agent | Model | When to Use |
|-----------------|-------|-------|-------------|
| Skills | `ai-artifacts-engineer` | Sonnet | Claude Code capabilities and workflows |
| Agent Prompts | `ai-artifacts-engineer` | Sonnet | Specialized subagent definitions |
| Context Files | `ai-artifacts-engineer` | Sonnet | Progress tracking, worknotes, observations |
| Workflow Automation | `ai-artifacts-engineer` | Sonnet | Multi-agent orchestration files |
| Symbol Graphs | `ai-artifacts-engineer` | Sonnet | Token-optimized codebase metadata |
| Slash Commands | `ai-artifacts-engineer` | Sonnet | YAML frontmatter command definitions |

**Examples:**

```markdown
Task("ai-artifacts-engineer", "Create a skill for API endpoint testing with security validation")

Task("ai-artifacts-engineer", "Design an agent prompt for TypeScript refactoring specialist")

Task("ai-artifacts-engineer", "Create Phase 3 progress tracking file following ONE-per-phase pattern")

Task("ai-artifacts-engineer", "Design slash command for database migration workflow")
```

**Key Insight:** AI artifacts require context engineering expertise. Use Sonnet model for sophisticated token optimization and invocation design.

## Contributing Back

If this becomes a shared/open-source repository:

### Creating Feature Branches

```bash
# Feature branches for new agents/commands
git checkout -b feature/agent-name

# Make changes and test thoroughly
Task("new-agent", "test")

# Commit with clear message
git commit -m "feat(agents/category): add new-agent description"
```

### Pull Request Process

1. Create descriptive PR title: `feat(agents/ai): add pattern-detection agent`
2. Include:
   - Description of new agent/command/skill
   - Test results
   - Breaking changes (if any)
   - Related agents/commands
3. Request review from project maintainers
4. Address feedback and iterate

### Documenting Breaking Changes

```markdown
## BREAKING CHANGE

- Renamed `old-agent` to `new-agent`
- Updated `agent:delegate` to use new pattern
- See MIGRATION.md for details
```

### Keeping Examples Current

Regularly update `examples/` directory:

- Update with current best practices
- Reflect latest features
- Remove outdated examples
- Add new use cases

## Troubleshooting

### Agent Not Found

**Problem**: `Task("agent-name", ...)` says agent not found

**Solution**:
1. Check agent filename matches name in frontmatter
2. Verify file is in correct agents/ category
3. Check YAML frontmatter syntax (use YAML validator)
4. Ensure agent file has correct extension (.md)

### Command Not Executing

**Problem**: `/command-name` doesn't execute

**Solution**:
1. Verify command file has valid YAML frontmatter
2. Check command `description` is present
3. Ensure `allowed-tools` list includes required tools
4. Test command syntax: `/command-name args`

### Script Permission Errors

**Problem**: `Permission denied` when running script

**Solution**:
```bash
# Make script executable
chmod +x scripts/script-name.sh

# Verify permissions
ls -l scripts/script-name.sh

# Source script instead of executing
source scripts/script-name.sh
```

### Symbol System Not Working

**Problem**: Symbol queries return no results

**Solution**:
1. Regenerate symbols: `/symbols:update`
2. Check symbols.config.json for correct paths
3. Verify domain configuration is correct
4. Test with `/symbols:query --all` to see all symbols

### YAML Frontmatter Invalid

**Problem**: Agent/command doesn't load due to frontmatter error

**Solution**:
1. Validate YAML at [yamllint.com](https://www.yamllint.com/)
2. Check for:
   - Missing colons after field names
   - Inconsistent indentation
   - Unquoted special characters
   - Invalid list syntax

### Variable Substitution Not Working

**Problem**: {{VARIABLES}} not being replaced

**Solution**:
1. Check variable names use `{{SCREAMING_SNAKE_CASE}}`
2. Verify variable is defined in config
3. Run substitution script with correct source/target
4. Check for typos in variable names

## References

### Key Documentation

- **[TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md)** - Complete customization guide with variable documentation
- **[README.md](./README.md)** - Repository overview and quick start
- **[examples/README.md](./examples/README.md)** - MeatyPrompts-specific examples
- **[scripts/README.md](./scripts/README.md)** - All available utility scripts
- **[skills/symbols/SKILL.md](./skills/symbols/SKILL.md)** - Symbol system comprehensive guide

### External References

- **[Claude Code Documentation](https://claudecode.anthropic.com/)** - Official Claude Code docs
- **[Markdown Syntax](https://www.markdownguide.org/)** - Markdown reference
- **[YAML Specification](https://yaml.org/)** - YAML reference

### Related Files

- **`settings.json`** - Claude Code configuration
- **`config/subagents.json`** - Agent invocation rules
- **`hooks/`** - Pre/post-commit hooks
- **`templates/`** - Reusable templates

## FAQ

**Q: How do I add a new agent?**
A: Create a file in `agents/[category]/[name].md` with YAML frontmatter and agent prompt. See "Creating New Agents" section.

**Q: What's the difference between agents and commands?**
A: Agents are for complex workflows and reasoning. Commands are for quick, focused operations. See "Common Patterns" section.

**Q: How do I customize this for my project?**
A: Follow "Customization for Your Project" section and use TEMPLATIZATION_GUIDE.md to replace variables.

**Q: Can I add my own agents/commands?**
A: Yes! Follow the templates and conventions in existing agents/commands of the same category.

**Q: How do I test changes before committing?**
A: Use `Task()` for agents and `/command` for commands. See "Testing Your Changes" section.

**Q: What if an agent fails or gives wrong output?**
A: Check agent prompt, verify tools are available, test with simpler task, review logs.

**Q: Can I use this for multiple projects?**
A: Yes! Fork or copy the repository and customize using TEMPLATIZATION_GUIDE.md.

**Q: How often should I update from upstream?**
A: If using submodules, pull regularly to get improvements. Test before using updates.

## Getting Help

### Documentation

- See [TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md) for variable documentation
- See [examples/](./examples/) for real-world examples
- Check agent frontmatter "description" field for when to use

### Common Issues

1. **Agent won't load** - Check YAML frontmatter syntax
2. **Command fails** - Verify argument syntax and available tools
3. **Script error** - Make executable with `chmod +x` and check error messages
4. **Symbol system issues** - Run `/symbols:update` to regenerate

### Support

- Review existing agents in same category as reference
- Check example files for patterns
- Refer to external tool documentation (Claude Code, Git, etc.)

## Version History

- **2025-11-05** - Initial CLAUDE.md created
  - 50 agents across 9 categories documented
  - 55 commands across 11 categories documented
  - Complete customization guide with examples
  - Troubleshooting and FAQ sections

---

**Last Updated**: 2025-11-05

This operating manual provides comprehensive guidance for working with the Claude Code configuration repository. For project-specific guidance, see [MeatyPrompts CLAUDE.md](../CLAUDE.md).

For questions about customization, see [TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md).

For agent-specific guidance, see the agent file itself — the frontmatter `description` field always includes examples of when to use that agent.
