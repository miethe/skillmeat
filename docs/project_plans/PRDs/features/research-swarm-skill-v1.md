---
title: 'PRD: Research Swarm Skill'
description: A specialized, high-capability skill for deep research decomposition,
  execution, and synthesis using the Workflow Engine.
audience:
- users
- prompt-engineers
tags:
- prd
- skill
- research
- swarm
- synthesis
created: 2026-02-02
updated: 2026-02-02
category: product-planning
status: draft
related:
- /docs/project_plans/PRDs/features/workflow-orchestration-v1.md
schema_version: 2
doc_type: prd
feature_slug: research-swarm-skill
---
# PRD: Research Swarm Skill

**Feature Name:** Research Swarm Skill
**Filepath Name:** research-swarm-skill-v1
**Date:** 2026-02-02
**Version:** 1.0
**Status:** Draft
**Priority:** MEDIUM (High Value Application)

## 1. Executive Summary

The Research Swarm is a specialized "Super Skill" that demonstrates the power of the SkillMeat platform. It utilizes the **Workflow Orchestration Engine** to spin up a roster of specialized agents (Scout, Skeptic, Synthesizer) to tackle complex research goals. It enforces evidence rules and produces structured "Research Packs" as artifacts.

## 2. Goals

* **Decomposition:** Break vague queries ("Analyze vector DB market") into concrete tasks.
* **Anti-Hallucination:** Enforce a "Skeptic" role that specifically looks for counter-evidence.
* **Artifact Generation:** Produce stable Markdown outputs (`findings.md`, `gaps.md`) that can be used as Context Modules for subsequent engineering tasks.

## 3. Functional Specifications

### 3.1 The Agent Roster
The skill generates a dynamic workflow containing:
1.  **Literature Scout:** Scans docs/web for primary sources.
2.  **Code Scout:** Greps repositories for implementation details.
3.  **Skeptic:** Reviews findings for contradictions or weak citations.
4.  **Synthesizer:** Compiles the final pack.

### 3.2 Evidence & Output Rules
* **Citation Requirement:** Every assertion in `findings.md` must link to a URL or File Path.
* **Conflict Detection:** The Synthesizer must explicitly list contradictions between sources in `disagreements.md`.

### 3.3 Integration with Memory System
* The Swarm writes short-lived "Research Memories" into the AutoContext system (PRD 1).
* It emits a "Research Context Module" that developers can attach to their coding workflows to ensure code aligns with research findings.

## 4. User Flow

1.  **Trigger:** User runs `skillmeat run research-swarm "Topic"`.
2.  **Plan:** The skill presents a generated breakdown of sub-agents and tasks.
3.  **Approve:** User confirms the plan.
4.  **Execution:** SkillMeat orchestrates the parallel execution of scouts.
5.  **Review:** User reviews the generated `research_pack` artifact in the Web UI.
6.  **Promote:** User clicks "Promote to Context" to make these findings available to the engineering team.

## 5. Success Metrics

* **Reuse Rate:** How often generated Research Packs are referenced in subsequent workflows.
* **Citation Density:** Average number of valid citations per paragraph of output.
