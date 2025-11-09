---
title: "Claude Code Professional Configuration"
description: "A comprehensive, production-ready Claude Code configuration featuring 50+ specialized agents, 55+ automation commands, and battle-tested utilities for professional software development"
audience: [developers, ai-agents, devops]
tags: [claude-code, configuration, agents, commands, automation, development-tools]
created: 2025-11-05
updated: 2025-11-05
category: configuration-deployment
status: published
related:
  - ./CLAUDE.md
  - ./TEMPLATIZATION_GUIDE.md
  - ./examples/README.md
  - ./scripts/README.md
---

# Claude Code Professional Configuration

> A comprehensive, production-ready Claude Code configuration featuring 50+ specialized agents, 55+ automation commands, and battle-tested utilities for professional software development.

[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-compatible-blue.svg)](https://claude.com/claude-code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version: 1.0.0](https://img.shields.io/badge/Version-1.0.0-green.svg)](#version)
[![Battle-Tested](https://img.shields.io/badge/Battle--Tested-Production-orange.svg)](#key-features)

---

## Quick Overview

This repository contains a comprehensive Claude Code configuration system originally developed for **MeatyPrompts**, a production-grade prompt management platform, and now generalized for use across any project. It provides everything needed to orchestrate complete software development workflows with AI-powered agents.

The system includes **50+ specialized agents** organized across 9 categories (AI, Architecture, Development, Project Management, Code Review, Technical Writing, UI/UX, and Debugging), **55+ automation commands**, **11 battle-tested utility scripts**, and a powerful **symbols system** that reduces token usage by 95-99% during codebase exploration.

Whether you're a solo developer, small team, or large organization, this configuration provides production-ready templates, real-world examples, and comprehensive documentation to accelerate development workflows.

---

## Key Features

### 🤖 50+ Specialized Agents (9 Categories)

Highly specialized agents for every aspect of software development:

- **AI Team** (3 agents) - Codebase exploration, symbol engineering, agent creation
- **Architects** (6 agents) - Backend, frontend, data layer, Next.js, system design, API contracts
- **Development Team** (11 agents) - Backend, Python, TypeScript, frontend, mobile, UI specialists
- **Fix Team** (5 agents) - Debugging, refactoring, extended-thinking analysis
- **Project Management** (5 agents) - PRD writing, feature planning, implementation planning, roadmaps
- **Reviewers** (8 agents) - Code review, task validation, accessibility auditing, contract validation
- **Technical Writers** (4 agents) - Documentation, API docs, OpenAPI, AsyncAPI specialists
- **UI/UX Team** (5 agents) - UI design, UX research, accessibility, design systems
- **Web Optimization** (3 agents) - Performance optimization, web-specific improvements

### ⚡ 55+ Automation Commands

Ready-to-use slash commands for every workflow:

- **Dev Commands** (12 commands) - Feature creation, story implementation, phase execution, PR preview
- **PM Commands** (8 commands) - User stories, ADR creation, spike documents, feature requests
- **Artifact Commands** (8 commands) - Symbol updates, READMEs, API docs, contract generation
- **Analysis Commands** (7 commands) - Architecture validation, violation scanning, test analysis
- **Integration Commands** (5 commands) - Linear, GitHub, Trello integration tasks
- **Utility Commands** (15 commands) - Memory management, learning capture, testing, refactoring

### 🔧 Battle-Tested Utilities (11 Scripts, 168KB)

Production-ready bash and Python utilities:

- **Architecture validation** - Layer checks, violation scanning
- **Symbol graph generation** - Token-efficient codebase navigation (95-99% reduction)
- **Contract validation** - OpenAPI and AsyncAPI schema validation
- **Git operations** - Change detection, commit analysis
- **JSON/YAML utilities** - Validation, formatting, transformation
- **Comprehensive reporting** - Statistics, analysis, tracking

See [`scripts/README.md`](./scripts/README.md) for complete documentation.

### 🧠 Symbols System (95-99% Token Efficiency)

Unique token-efficient codebase navigation:

- Pre-generated metadata about functions, classes, components, and types
- Domain-specific symbol files (API, UI, Web, Tests) for targeted loading
- Precise file:line references for quick navigation
- Architectural awareness with layer tagging
- Reduces token usage by 95-99% compared to full code context
- Performance: Get 139+ symbols from 38+ files in 0.1 seconds

See [`skills/symbols/SKILL.md`](./skills/symbols/SKILL.md) for comprehensive details.

### 📚 Production-Ready Examples

Real-world examples from MeatyPrompts:

- Multi-phase feature implementation with progress tracking
- Architecture validation and enforcement
- Automated documentation generation
- Symbol-based codebase exploration workflows
- PM workflow automation (Linear, GitHub, Trello)

See [`examples/README.md`](./examples/README.md) for detailed examples.

### 🎯 Comprehensive Templatization Support

Fully customizable for any project:

- Variable placeholders (`{{PROJECT_NAME}}`, `{{ARCHITECTURE_LAYERS}}`, etc.)
- Extensive customization guide with step-by-step instructions
- Support for different architectures, PM workflows, and standards
- Easy integration with your project's specific needs

See [`TEMPLATIZATION_GUIDE.md`](./TEMPLATIZATION_GUIDE.md) for detailed instructions.

---

## Quick Start

Get up and running in 3 simple steps. Choose your preferred installation method:

### Option 1: Direct Copy (Simplest)

```bash
# Copy configuration to your project
cp -r /path/to/claude-export/.claude /your/project/.claude

# Customize for your project (optional)
# Edit agents, commands, and settings for your needs
```

**Best for:** Single-project use, one-time setup, projects without git

---

### Option 2: Git Submodule (Recommended)

```bash
# Add as submodule for easy updates
git submodule add <repository-url> .claude-config

# Create symlink to make it available as .claude
ln -s .claude-config/.claude .claude

# Customize (optional - changes stay in your project)
# Edit .claude files (changes don't affect upstream)
```

**Best for:** Teams, projects wanting upstream updates, version control

---

### Option 3: Clone and Customize

```bash
# Clone and customize for your project
git clone <repository-url> claude-config
cd claude-config

# Follow customization guide
cat TEMPLATIZATION_GUIDE.md

# Replace {{VARIABLES}} with your project-specific values
# Test new agents and commands
# Commit customized version
```

**Best for:** Organizations with significant customization, multiple projects

---

## What's Inside

### Directory Structure

```
.
├── agents/                          # 50+ specialized agents (9 categories)
│   ├── ai/                          # AI exploration & symbol experts
│   ├── architects/                  # System & layer architects
│   ├── dev-team/                    # Implementation engineers
│   ├── fix-team/                    # Debugging & refactoring experts
│   ├── pm/                          # Product management & planning
│   ├── reviewers/                   # Code review & validation
│   ├── tech-writers/                # Documentation specialists
│   ├── ui-ux/                       # UI/UX design experts
│   └── web-optimize-team/           # Web performance specialists
│
├── commands/                        # 55+ automation commands
│   ├── [dev-commands].md           # Feature & development workflows
│   ├── [pm-commands].md            # Planning & documentation
│   ├── [artifact-commands].md      # README, API docs, symbols
│   ├── [analysis-commands].md      # Code analysis & validation
│   ├── [integration-commands].md   # External tool integrations
│   └── [utility-commands].md       # Testing, refactoring, utilities
│
├── scripts/                         # 11 utility scripts
│   ├── validate-architecture.sh    # Layer & dependency validation
│   ├── generate-symbols.sh         # Symbol graph generation
│   ├── validate-contracts.sh       # OpenAPI/AsyncAPI validation
│   └── [other utilities]           # Git, JSON, YAML, reporting
│
├── skills/                          # Reusable skill frameworks
│   └── symbols/                    # Symbol system skill
│
├── templates/                       # Reusable document templates
│   ├── implementation-plan.md      # Multi-phase implementation planning
│   ├── spike-document.md           # Technical spike template
│   ├── task-breakdown.md           # Task decomposition
│   └── feature-request.md          # Feature request template
│
├── config/                          # Configuration files
│   ├── settings.json               # Main configuration
│   └── [other configs]             # Additional settings
│
├── examples/                        # Real-world MeatyPrompts examples
│   ├── plans/                      # Implementation plan examples (8 files)
│   ├── progress/                   # Progress tracking examples (16 files)
│   └── worknotes/                  # Development notes examples
│
├── CLAUDE.md                        # Complete operating manual
├── TEMPLATIZATION_GUIDE.md         # Customization guide
├── README.md                        # This file
└── settings.json                    # Configuration
```

### Agents by Category

#### AI Team (3 agents)
- **codebase-explorer** - Fast pattern discovery (0.1 seconds, 95-99% token reduction)
- **explore** - Deep analysis with full context (2-3 minutes, complete understanding)
- **symbol-engineer** - Symbol system expert and generator

#### Architects (6 agents)
- **lead-architect** - Senior system architect (orchestration, decisions)
- **backend-architect** - Backend/API patterns and design
- **frontend-architect** - Frontend/React patterns and design
- **nextjs-architecture-expert** - Next.js and App Router specialist
- **data-layer-expert** - Database, persistence, and data modeling
- **api-contract-expert** - OpenAPI and AsyncAPI design

#### Development Team (11 agents)
- **backend-engineer** - Backend implementation
- **python-backend-engineer** - Python-specific backend work
- **frontend-developer** - Frontend/React implementation
- **typescript-specialist** - TypeScript type systems and patterns
- **mobile-app-builder** - React Native/Expo expertise
- **ui-engineer** - UI component implementation
- **next-js-developer** - Next.js App Router development
- **tailwind-css-expert** - Tailwind styling and design tokens
- **database-engineer** - Database implementation and optimization
- **devops-engineer** - Infrastructure and deployment
- **api-integration-specialist** - Third-party API integration

#### Fix Team (5 agents)
- **ultrathink-debugger** - Extended-thinking deep analysis
- **refactoring-expert** - Code refactoring and improvements
- **performance-debugger** - Performance analysis and optimization
- **test-debugger** - Test failure diagnosis
- **architecture-debugger** - Structural and design issues

#### Project Management (5 agents)
- **prd-writer** - Product requirement documents
- **implementation-planner** - Detailed implementation planning
- **feature-architect** - Feature definition and scope
- **roadmap-strategist** - Product roadmap planning
- **spike-coordinator** - Technical spike planning

#### Reviewers (8 agents)
- **code-reviewer** - Comprehensive code review
- **task-completion-validator** - Task acceptance validation
- **accessibility-auditor** - A11y compliance checking
- **contract-reviewer** - OpenAPI/AsyncAPI review
- **architecture-reviewer** - Design pattern review
- **security-reviewer** - Security analysis
- **performance-reviewer** - Performance impact review
- **testing-reviewer** - Test coverage review

#### Technical Writers (4 agents)
- **documentation-writer** - User guides, API docs, integration guides (90% of docs)
- **documentation-complex** - Complex multi-system documentation
- **documentation-planner** - Documentation strategy planning
- **openapi-specialist** - OpenAPI schema documentation

#### UI/UX Team (5 agents)
- **ui-designer** - Component and interface design
- **ux-researcher** - User research and testing
- **accessibility-expert** - WCAG and accessibility design
- **design-system-architect** - Design system and component libraries
- **interaction-designer** - Interaction patterns and flows

#### Web Optimization (3 agents)
- **web-performance-expert** - Performance optimization
- **seo-specialist** - Search engine optimization
- **web-security-expert** - Web security hardening

---

## Installation Methods Comparison

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Direct Copy** | Simple, no dependencies | No upstream updates | One-time use, quick setup |
| **Git Submodule** | Easy updates, separate customization | Slightly complex setup | Teams, maintaining upstream sync |
| **Fork & Customize** | Full control, version history | Manual upstream merges | Organizations, significant customization |

---

## Core Documentation

### Getting Started

- **[CLAUDE.md](./CLAUDE.md)** - Complete operating manual
  - Prime directives and core principles
  - Repository structure and organization
  - Creating new agents and commands
  - Customization guidelines
  - ~38KB comprehensive guide

### Customization

- **[TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md)** - Adapt for your project
  - Variable naming conventions
  - Core variable definitions (identity, architecture, workflow, etc.)
  - Step-by-step customization instructions
  - Testing and validation
  - Real-world examples
  - ~34KB detailed guide

### Reference & Examples

- **[examples/README.md](./examples/README.md)** - Real-world MeatyPrompts examples
  - Implementation plans (8 files)
  - Progress tracking (16 files)
  - Worknotes and context
  - Pattern demonstrations

- **[scripts/README.md](./scripts/README.md)** - Utility scripts documentation
  - Architecture validation
  - Symbol generation
  - Contract validation
  - Testing utilities
  - Complete script reference

- **[skills/symbols/SKILL.md](./skills/symbols/SKILL.md)** - Symbols system expertise
  - 95-99% token reduction techniques
  - Symbol files organization
  - Domain-specific loading
  - Performance patterns

---

## Recommended Usage Patterns

### 1. Fast Codebase Exploration (0.1 seconds)

Use symbol-based exploration for quick discovery:

```
Task("codebase-explorer", "Find all authentication endpoints in the API")
→ Get 50+ relevant symbols from 10+ files in 0.1 seconds
→ Review specific files as needed
→ 95-99% token reduction
```

### 2. Deep Architecture Analysis (2-3 minutes)

Use explore for comprehensive analysis:

```
Task("explore", "Analyze authentication system across API, middleware, and frontend")
→ Get full context from 300+ files
→ Understand all patterns and connections
→ Perfect for major architectural decisions
```

### 3. Multi-Phase Feature Implementation

Use planning agents with progress tracking:

```
Task("implementation-planner", "Plan 3-phase prompt card refactor")
→ Get detailed implementation plan
→ Create progress tracker during implementation
→ Reference examples/ for real-world patterns
```

### 4. Code Review & Validation

Use specialized reviewers for comprehensive feedback:

```
Task("code-reviewer", "Review PR for architecture compliance")
Task("accessibility-auditor", "Check WCAG compliance")
Task("contract-reviewer", "Validate API schemas")
```

### 5. Documentation Generation

Use documentation writers for 90% of docs (use complex writer only for 5+ service synthesis):

```
Task("documentation-writer", "Create API documentation for new endpoints")
Task("documentation-writer", "Write component documentation with accessibility notes")
```

---

## Customization Quick Start

To customize this configuration for your project:

### Step 1: Replace Core Variables

Edit `settings.json` and agent files:

```bash
# Replace project-specific variables
find .claude -type f -name "*.md" | xargs sed -i 's/{{PROJECT_NAME}}/YourProject/g'
find .claude -type f -name "*.md" | xargs sed -i 's/{{PROJECT_DESCRIPTION}}/Your description/g'
```

### Step 2: Customize Settings

Edit `.claude/config/settings.json`:
- Project name and description
- Architecture layers and patterns
- PM workflow and tools
- API structure and conventions

### Step 3: Test Agents

Run test tasks to verify agents work with your codebase:

```
Task("codebase-explorer", "Find all route definitions in my API")
Task("backend-architect", "Analyze my database schema for compliance")
```

### Step 4: Update Examples

Replace examples/plans and examples/progress with your project's documents

See [TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md) for comprehensive customization instructions.

---

## Requirements

### Mandatory

- **Claude Code CLI** (latest version)
  - Download: https://claude.com/claude-code
  - Enables `/command` slash command execution
  - Provides AI agent orchestration

- **Claude 3.5 Sonnet or later**
  - Used by agents for code analysis and generation
  - Latest models for best results

### Recommended

- **Git** (for submodule support and version control)
  - Enables `git submodule` installation method
  - Track changes to customizations

- **Bash** (for scripts and hooks)
  - Unix-like environment (macOS, Linux, WSL)
  - Windows: Use WSL or Git Bash

### Optional

- **Python 3.8+** (for advanced scripts)
  - Symbol generation and analysis
  - Contract validation

---

## Quick Reference: Key Commands

### Get Started
```bash
/implement-feature "Feature description"     # Multi-phase feature planning
/create-prd "Feature description"             # Product requirement document
/validate-task                                # Validate task completion
```

### Code Analysis
```bash
/symbols-load {{SYMBOL_FILE}}                # Load symbol metadata
/symbols-query "search terms"                 # Search codebase efficiently
/validate-architecture                        # Check layer compliance
```

### Documentation
```bash
/generate-readme {{TARGET_PATH}}              # Create README
/generate-api-docs {{ROUTER_FILE}}            # API documentation
/update-symbols                               # Regenerate symbol metadata
```

### Development Workflow
```bash
/story-implementation "Epic-123"              # Implement user story
/review-pr                                    # Code review
/run-tests {{TEST_PATH}}                      # Execute tests
```

See [CLAUDE.md](./CLAUDE.md) for complete command reference.

---

## Examples & Use Cases

### Use Case 1: Multi-Phase Feature Implementation

1. Create implementation plan with `/implement-feature`
2. Reference examples/ for MeatyPrompts patterns
3. Track progress with progress tracker
4. Use codebase-explorer for quick discovery
5. Use specialized architects for design decisions

See: `examples/plans/MP-NAV-UI-005-plan.md`

### Use Case 2: Architecture Validation

1. Use `validate-architecture` to check layer compliance
2. Use backend-architect for API design review
3. Use data-layer-expert for database schema review
4. Use performance-reviewer for optimization

### Use Case 3: Automated Documentation

1. Generate API docs with `/generate-api-docs`
2. Create component docs with documentation-writer
3. Generate README with `/generate-readme`
4. Update symbol metadata with `/update-symbols`

### Use Case 4: Efficient Codebase Navigation

1. Start with `codebase-explorer` (0.1 seconds)
2. Get symbol references to key files
3. Deep dive with `explore` if needed (2-3 minutes)
4. 95-99% token savings for large codebases

---

## Contributing

### Reporting Issues

1. Check [GitHub Issues](https://github.com/your-org/claude-export/issues)
2. Provide clear reproduction steps
3. Include output and environment details
4. Reference CLAUDE.md if configuration-related

### Adding New Agents

1. Review similar agents in same category
2. Follow YAML frontmatter format
3. Test with `Task("your-agent", "test task")`
4. Document in CLAUDE.md
5. Submit PR with detailed description

### Sharing Improvements

1. Fork the repository
2. Create feature branch
3. Test thoroughly
4. Submit PR with use cases and examples
5. Include any CLAUDE.md updates

See [CLAUDE.md](./CLAUDE.md#creating-new-agents) for detailed agent creation guide.

---

## Version History

- **1.0.0** (2025-11-05) - Initial release
  - 50+ agents across 9 categories
  - 55+ automation commands
  - 11 utility scripts (168KB)
  - Symbols system with 95-99% token reduction
  - Production examples from MeatyPrompts
  - Complete customization guide

---

## License

MIT License - See LICENSE file for details

---

## Credits

- **Originally Developed For:** MeatyPrompts (Prompt Management & Authoring Platform)
- **Generalized For:** Community use and any software development project
- **Built On:** Claude Code by Anthropic
- **Contributors:** AI-assisted development with Claude 3.5 Sonnet

---

## Support & Community

### Documentation
- **[CLAUDE.md](./CLAUDE.md)** - Complete operating manual (38KB)
- **[TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md)** - Customization guide (34KB)
- **[examples/README.md](./examples/README.md)** - Real-world examples
- **[scripts/README.md](./scripts/README.md)** - Utility documentation

### Get Help
- Review similar agents in `agents/` directory
- Check examples in `examples/` for patterns
- Read CLAUDE.md for operating principles
- See TEMPLATIZATION_GUIDE.md for customization help

### Discuss & Share
- Open GitHub Discussions (if enabled)
- Share your customizations and use cases
- Contribute improvements back to community

---

## Quick Navigation

| Want to... | Start here |
|-----------|-----------|
| Get started | [Quick Start](#quick-start) section above |
| Understand how to use this | [CLAUDE.md](./CLAUDE.md) |
| Customize for your project | [TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md) |
| See real examples | [examples/README.md](./examples/README.md) |
| Learn about utilities | [scripts/README.md](./scripts/README.md) |
| Understand symbols system | [skills/symbols/SKILL.md](./skills/symbols/SKILL.md) |
| Create new agents | [CLAUDE.md](./CLAUDE.md#creating-new-agents) section |

---

## Next Steps

1. **Read** [CLAUDE.md](./CLAUDE.md) for complete operating manual
2. **Customize** using [TEMPLATIZATION_GUIDE.md](./TEMPLATIZATION_GUIDE.md)
3. **Explore** examples in [examples/](./examples/) directory
4. **Test** agents with your project's codebase
5. **Deploy** to your team and project

**Questions?** Check the relevant documentation files above or review the examples directory for patterns and best practices.
