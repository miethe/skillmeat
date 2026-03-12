---
title: 'PRD: Enterprise Governance & 3-Tier Scope Architecture'
description: 'Expansion of SkillMeat RBAC and ownership models to support a full 3-tier hierarchy (User, Team, Enterprise) with forced inheritance and global governance controls.'
audience:
  - ai-agents
  - backend-architects
  - product-managers
tags:
  - prd
  - planning
  - rbac
  - enterprise
  - governance
  - sync-engine
created: 2026-03-11
status: draft
category: product-planning
feature_slug: enterprise-governance-3-tier
related_documents:
  - docs/project_plans/PRDs/features/aaa-rbac-foundation-v1.md
  - docs/project_plans/PRDs/refactors/enterprise-db-storage-v1.md
  - docs/project_plans/PRDs/enhancements/versioning-merge-system-v1.md
  - docs/project_plans/design-specs/ownership-resolution-and-membership-semantics.md
---

# PRD: Enterprise Governance & 3-Tier Scope Architecture

## 1. Executive Summary

As SkillMeat scales into larger organizational environments, the current two-tier ownership model (`User`, `Team`) is insufficient for platform engineering teams that require global governance. Organizations need to push mandatory compliance standards, security protocols, and "Golden Context" across all teams simultaneously without relying on team-level opt-in. 

This PRD formalizes the **Enterprise** tier as the absolute data boundary and highest level of administrative control. It expands the existing RBAC and storage foundations to support a strict inheritance hierarchy (`Enterprise > Team > User`), introduces immutable global artifacts, and overhauls the sync engine to support forced, top-down rollouts.

**Priority:** HIGH (Critical for Enterprise SaaS positioning)  
**Complexity:** LARGE

## 2. Goals & Outcomes

* **Global Governance:** Allow platform/system administrators to create and enforce artifacts at the `Enterprise` scope that affect all teams and users within a tenant.
* **Compliance Enforcement:** Introduce an "immutable" or "forced override" flag for artifacts, preventing local/team modifications of critical security rules.
* **Zero-Friction Onboarding:** Implement "Enterprise Collections" so new users/teams inherit organizational standards instantly on Day 0 (curing "agent amnesia").
* **Hierarchical Sync Resolution:** Update the sync and merge engines to understand authority. Enterprise dictates to Team; Team dictates to User. 

## 3. Context & Background

### Current State vs. Limitations
* **Tenancy:** We currently have a `tenant_id` on all artifacts/collections, which successfully isolates one enterprise's data from another.
* **Ownership:** The `owner_type` ENUM only supports `user` and `team`. To share globally within a tenant today, assets must be placed in a pseudo-team or rely on `visibility: public`, which lacks hierarchical authority.
* **Sync Logic:** Our current `SyncManager` relies heavily on standard three-way merges or user-initiated pulls. It does not support a "forced overwrite" where a higher authority forcefully patches a lower-level context without prompting for conflict resolution.

## 4. Scope & Requirements

### 4.1 Schema & Data Model Expansions
Modify the foundational database schema to represent the top tier.
* **`owner_type` ENUM:** Expand the existing enum to include `enterprise` (e.g., `ENUM('user', 'team', 'enterprise')`). 
* **Immutability Flag:** Add a boolean `enforce_override` (or `is_immutable`) field to the `Artifact` and `Collection` models.
    * *Rule:* If `is_immutable = True`, the artifact cannot be edited or overridden by anyone lacking explicit permission at the `owner_type` level where it was created.

### 4.2 RBAC & Role Refinement
Map existing system roles explicitly to the new tier.
* **`system_admin` refinement:** Map this role specifically to the `Enterprise` owner type. A `system_admin` is the only entity that can author, update, or delete `Enterprise`-scoped artifacts.
* **Scope Isolation:** Ensure `team_admin` roles cannot modify `Enterprise` artifacts, even if those artifacts are materialized within their team's workspace.

### 4.3 Inheritance & Sync Engine Overhaul
This is the most critical logic update, fundamentally altering how `skillmeat/core/sync.py` and `MergeEngine` resolve conflicts.
* **Hierarchy Awareness:** The sync engine must be updated to evaluate state using the `Enterprise > Team > User` dominance path.
* **Forced Rollout (Fast-Forward Overwrite):** * If an `Enterprise`-scoped artifact with `enforce_override=True` is updated by a `system_admin`, the sync engine must bypass the interactive three-way merge prompt for all downstream collections.
    * It should execute an automatic fast-forward overwrite on all connected Team and User collections, logging the action in the artifact's history as an `Administrative Override`.
* **Shadowing/Layering:** Allow Users to "shadow" an Enterprise artifact *only if* `enforce_override=False`. If False, the standard three-way merge applies.

### 4.4 Global Day-0 Collections
* **Enterprise Collections:** Create a new construct for globally inherited collections. 
* **Auto-Binding:** When a new `Team` or `User` is provisioned under a `tenant_id`, they automatically inherit a read-only dependency link to the active "Enterprise Global Collection". 

## 5. User Experience (UX) & Workflows

1.  **Platform Engineer (System Admin):**
    * Logs into the global dashboard. Creates a new Context Entity called `CLAUDE.md (Security Policy)`.
    * Sets Owner to `Enterprise` and toggles `Enforce Overrides` to ON.
    * Clicks "Deploy Globally."
2.  **Team Admin:**
    * Sees the `CLAUDE.md` appear in their Team Collection with a "Lock" icon and an "Enterprise Managed" badge. They cannot edit the core file, but can add Team-specific supplementary context if permitted.
3.  **End User (Developer):**
    * Runs `skillmeat sync` or scaffolding commands in their CLI. The Enterprise security policy is automatically injected into their `.claude/` directory, overwriting any previous local hacks, ensuring total compliance.

## 6. Implementation Phases

* **Phase 1: Schema & Data Layer (Backend)**
    * Create Alembic migrations extending `owner_type` and adding `enforce_override` flags to `models.py`.
    * Update DTOs and SQLAlchemy repository layers to support querying by the new enterprise scope.
* **Phase 2: RBAC Refinement (Backend)**
    * Update `AuthContext` middleware to correctly validate `system_admin` against the new `Enterprise` ownership logic.
* **Phase 3: Sync & Merge Engine (Core)**
    * Refactor `skillmeat/core/sync.py` to intercept `enforce_override` flags.
    * Build the top-down cascading update mechanism for Enterprise artifacts.
* **Phase 4: UI & Badging (Frontend)**
    * Update the Artifact Modal and Cards to display "Enterprise" badges, Lock icons for immutable files, and disable "Edit" buttons for lower-tier users viewing top-tier assets.

## 7. Open Questions / Assumptions

* **Q1: Cascade Performance:** If an Enterprise has 5,000 users, and an admin pushes an enforced update, will the cascaded sync operation block the database?
    * *Recommendation:* Forced global rollouts should be pushed to a background task queue (e.g., Celery/Redis) rather than processed synchronously in the API request.
* **Q2: Soft vs. Hard Deletes for Enterprise:** If a system admin deletes a global artifact, should it violently strip it from all local developer drives?
    * *Recommendation:* Yes, but issue an in-app "Warning: Destructive Sync" notification via the Notification System (v1) prior to local file removal.
