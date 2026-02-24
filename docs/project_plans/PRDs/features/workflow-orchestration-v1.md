---
title: 'PRD: Workflow Orchestration Engine'
description: A workflow builder for defining multi-stage agentic tasks with specific
  role assignments and artifact binding.
audience:
- developers
- power-users
tags:
- prd
- workflow
- orchestration
- automation
- agents
created: 2026-02-02
updated: 2026-02-02
category: product-planning
status: planned
related:
- /docs/project_plans/PRDs/features/memory-context-system-v1.md
- /skillmeat/core/artifact.py
schema_version: 2
doc_type: prd
feature_slug: workflow-orchestration
---
# PRD: Workflow Orchestration Engine

**Feature Name:** Workflow Orchestration Engine (Workflow Composer)
**Filepath Name:** workflow-orchestration-v1
**Date:** 2026-02-02
**Version:** 1.0
**Status:** Draft
**Priority:** MEDIUM (Depends on Memory System)

## 1. Executive Summary

The Workflow Orchestration Engine elevates SkillMeat from managing *tools* (artifacts) to managing *processes*. It allows users to define "Workflows" as artifacts—structured JSON/YAML files that define stages (e.g., Research -> Plan -> Code -> Review) and assign specific SkillMeat artifacts (Agents/Skills) to roles within those stages.

## 2. Context & Background

**Problem:**
Currently, users must manually invoke different agents or skills for different parts of a job. "Shipping a feature" involves ad-hoc context switching.

**Solution:**
Create a `Workflow` artifact type. This allows users to standardize "How we ship work" per project. Workflows are predictable, shareable, and version-controlled via the existing Collection architecture.

## 3. Functional Requirements

### 3.1 Workflow Artifact Schema
A new artifact type `WORKFLOW` managed by `ArtifactManager`.
```json
{
  "workflow_id": "sdlc-feature-ship",
  "stages": [
    {
      "id": "research",
      "roles": { "primary": "agent:researcher-v1" },
      "context_policy": { "modules": ["ctx:repo-rules"] }
    },
    {
      "id": "implementation",
      "roles": { "primary": "agent:coder-v2", "tools": ["skill:git-ops"] }
    }
  ]
}

```

### 3.2 Role Assignment

* **Dynamic Binding:** Users can define roles (e.g., "Reviewer") in the workflow template, and bind them to specific artifacts (e.g., "Claude Sonnet", "Custom Linter") at runtime or project config level.
* **Project Overrides:** A project can define a `.skillmeat-workflow-overrides.toml` to swap agents without changing the shared workflow definition.

### 3.3 Execution Plan

* **Dry Run:** The CLI command `skillmeat workflow plan <name>` generates a roadmap of what agents will run and what context will be injected.
* **Handoffs:** Standardized format for passing state (artifacts, memory IDs) between stages.

## 4. User Experience

### 4.1 Workflow Builder (Web UI)

* **Drag-and-Drop Interface:** Visualize stages as nodes.
* **Artifact Picker:** Sidebar to drag existing Skills/Agents into workflow roles.
* **Context Binding:** Select which "Context Modules" (from PRD 1) apply to which stage.

### 4.2 Execution Dashboard

* Timeline view of the running workflow.
* Step-by-step logs showing which agent is active and what context it is consuming.

## 5. Integration Points

* **Collections:** Workflows are stored in `~/.skillmeat/collections/{name}/workflows/`.
* **Marketplace:** Workflows can be bundled and shared via `.skillmeat-pack`.
* **Memory System:** Workflows are the primary consumers of "Context Packs" defined in PRD 1.

## 6. Implementation Phases

**Phase 1: Schema & Core Logic**

* Define `Workflow` artifact type.
* Implement parsing and validation logic in `skillmeat/core/workflow.py`.

**Phase 2: CLI Execution**

* `skillmeat workflow run` command.
* Basic sequential execution logic.

**Phase 3: Visual Composer**

* Web UI for creating and editing workflows.
