# From Router-Coupled Storage to Repository-First Architecture

**Date**: 2026-03-06
**Author**: GPT 5.4
**Linked Feature**: repo-pattern-refactor-v1
**Related PR**: #109

PR `#109` completed one of the most important kinds of engineering work: the kind users do not see directly, but every future feature depends on. The `repo-pattern-refactor` moved SkillMeat’s API away from a model where routers reached straight into the filesystem and SQLite cache, and toward a hexagonal, repository-first design with explicit contracts, dependency injection, and backend replaceability. The result: **131 files changed, 87,285 lines added, and 6,869 removed** — executed across three implementation plans in approximately six days.

Before this work, too much of the storage model leaked upward into the HTTP layer. Routers were doing path resolution, filesystem reads and writes, direct SQLAlchemy work, cache synchronization, and request handling all in the same place. That made the code harder to test, harder to reason about, and expensive to evolve. It also created a serious architectural constraint: any move to enterprise storage, multi-tenant access control, or alternate backends would have required touching router logic all over the API surface.

## Why We Did It

The refactor was driven by a simple architectural requirement: the API needed a stable seam between business behavior and storage behavior. SkillMeat already had a split data model, with the filesystem acting as the source of truth and a SQLite-backed cache serving the web experience. That model worked, but the implementation details were spread across routers in a way that made the system tightly coupled to “local mode.”

An audit at the start of the project found **15 of 36 router files** importing `os`, `pathlib`, or `sqlite3` directly for data retrieval. The largest offender was `artifacts.py` at **9,400+ lines**, mixing HTTP handling, path resolution, filesystem I/O, and DB queries in a single layer. Beyond the filesystem imports, a follow-on audit uncovered **380+ direct SQLAlchemy session calls** scattered across 10 additional routers — `session.query()`, `session.add()`, `session.commit()` calls that reached past any abstraction directly into the ORM layer. Four entire domains (groups, context entities, marketplace sources, project templates) had no repository interface at all. And the same `resolve_project_path()` and `_normalize_artifact_path()` helper functions were duplicated in five or more places with no shared implementation.

The repository pattern solves that by defining storage contracts once, implementing them behind adapters, and letting routers depend on interfaces instead of concrete persistence details. In SkillMeat’s case, that also creates the path for two larger initiatives already planned: request-scoped authorization and future enterprise storage backends. Without this refactor, both of those efforts would have had to fight the codebase instead of building on it.

## What Changed

### The Contracts Layer

The first major change was the creation of `skillmeat/core/interfaces/` — a package that now holds every repository interface, DTO, and the `RequestContext` object that defines how the rest of the application talks to storage. What was originally scoped as six ABCs grew to **13 abstract repository interfaces** covering every data domain in the system. The interfaces file alone is **4,016 lines** with **154 abstract methods**. Alongside it, `dtos.py` defines **44 data transfer objects** (1,389 lines) as plain Python dataclasses with no ORM dependency — safe to use at any layer. Every repository method signature includes a `RequestContext` parameter as a placeholder for the RBAC authorization layer that was built immediately after.

```
skillmeat/core/interfaces/
├── repositories.py  — 4,016 lines, 13 ABCs, 154 abstract methods
├── dtos.py          — 1,389 lines, 44 DTOs
└── context.py       — 57 lines, RequestContext dataclass
```

### Local Repository Implementations

The second change was **10 concrete local repository implementations** in `skillmeat/core/repositories/`, totaling **8,831 lines** across the package. These adapters preserve SkillMeat’s existing write-through behavior — filesystem writes remain authoritative, with the SQLite cache synchronized behind the scenes — but they do so through a defined interface rather than ad hoc inline logic extracted from each router.

| File | Lines |
|------|-------|
| local_artifact.py | 1,613 |
| local_group.py | 1,162 |
| local_marketplace_source.py | 1,055 |
| local_project.py | 810 |
| local_settings_repo.py | 764 |
| local_collection.py | 765 |
| local_context_entity.py | 717 |
| local_deployment.py | 595 |
| local_project_template.py | 584 |
| local_tag.py | 437 |

The refactor changed the shape of the code, not the product’s local-first behavior. Every existing API contract — all response schemas, status codes, and pagination formats — remained identical throughout.

### Dependency Injection Wiring

The third change was centralizing the entire system through `skillmeat/api/dependencies.py` (now **999 lines**), which registers **18 typed DI aliases** covering all repositories. Instead of routers choosing storage mechanisms themselves, they declare a dependency and FastAPI resolves it. A single `config.EDITION` field controls which implementation is returned — `”local”` today, with the `”enterprise”` branch reserved for the next phase. Adding a new storage backend now means implementing the 13 ABCs; zero router changes are required.

### Router Migration

The highest-risk phase was migrating the routers themselves. This proceeded in batches across three implementation plans:

- **Plan 1 (repo-pattern-refactor-v1, 40 pts)**: Migrated the 15 routers with direct `os`/`pathlib` imports, including `artifacts.py`, `projects.py`, `user_collections.py`, `deployments.py`, and `context_entities.py`.
- **Plan 2 (repo-pattern-gap-closure-v1, 38 pts)**: Eliminated the 380+ direct SQLAlchemy session calls in 10 more routers that bypassed the interface layer entirely — including 180+ calls in `user_collections.py` alone and 70+ in `groups.py`. Also added 4 new ABCs and 4 new local implementations for the domains that had no interface coverage.
- **Plan 3 (repo-pattern-final-cleanup-v1, ~4 pts)**: Removed the final 39 residual `session.execute`/`session.flush` calls across `user_collections.py` and `artifact_history.py`.

The total effort across all three plans was approximately **82 story points** — and it concluded with a machine-verifiable grep audit confirming zero prohibited session patterns in any router file.

### Test Infrastructure

The refactor invested as heavily in safety rails as in the migration itself. Before the first router was touched, baseline test coverage was added for the 8 previously-untested routers, and a snapshot of `openapi.json` was captured to keep the refactor contractually honest. During migration, three new test infrastructure components were built:

| File | Lines |
|------|-------|
| tests/mocks/repositories.py | 1,719 |
| tests/test_repositories_coverage.py | 1,595 |
| tests/test_repositories_integration.py | 1,241 |

The mock repository layer means router unit tests no longer need a real filesystem or SQLite database. Tests that previously required environment setup now run in-process with configurable canned responses. The total test count grew to **134 test files** with 41 in the API surface alone.

## What It Achieved

### Backend Replaceability

The most consequential outcome is a concrete checklist for enterprise storage. Implementing all 13 ABCs now covers 100% of data access paths — every route, every endpoint, every query that the API can produce is intercepted by a repository interface. That means implementing the enterprise backend is purely additive work: write the implementations, add an `”enterprise”` branch to the factory providers in `dependencies.py`, and the swap happens at startup with no router changes.

### Immediate Unblocking

The refactor was PRD 1 of a three-PRD enterprise initiative. PRD 2 (AAA/RBAC Foundation) could not be implemented safely without a `RequestContext` threading through every data call — that context object is now in place on every repository method. PRD 3 (Enterprise DB Storage) could not swap backends without rewriting router logic — that logic is now entirely behind repository interfaces. Both of those follow-on efforts became straightforward once the seam existed. The RBAC work, in fact, launched and completed immediately after this refactor landed.

### Testability at Scale

Mock repositories and DI overrides mean more of the system can now be exercised without filesystem state. Integration tests verify write-through consistency — that the filesystem and DB cache always match after every mutation type — without the fragility of temporary directories and real SQLite instances. New contributors can write router tests entirely in-process.

### Architectural Policy

The refactor turned architectural intent into enforced policy. SkillMeat now has a documented, repository-first model rather than a loose convention. The design lives in the `skillmeat/core/interfaces/README.md`, in the rule files at `.claude/rules/`, and in the DI system itself. Routers are for HTTP concerns. Repositories are for data access. DTOs are the boundary between them. Adding new storage access anywhere that bypasses those conventions now requires actively working against the architecture rather than accidentally inheriting it.

## How AI Agents Made It Possible in Six Days

The scope of this work — 82 story points, 131 files, three sequential implementation plans — would typically occupy a backend team for several weeks. It was executed in approximately six days. That speed came from how the work was structured and delegated.

The effort used a team of specialized agents orchestrated by Claude Opus:

- **python-backend-engineer** (Sonnet 4.6) handled the bulk of implementation: local repository classes, DI wiring, mechanical router migrations, and the write-through integration tests.
- **backend-architect** (Sonnet 4.6) owned interface design — ensuring the 13 ABCs had correct signatures, complete `RequestContext` coverage, and proper DTO boundaries before a single implementation was written.
- **data-layer-expert** (Sonnet 4.6) built the write-through consistency tests and managed the SQLAlchemy session scoping work.
- **refactoring-expert** (Sonnet 4.6) handled the highest-blast-radius migrations — `user_collections.py` (180+ calls), `groups.py` (70+ calls), and the `artifacts.py` fallback cleanup.
- **task-completion-validator** (Sonnet 4.6) ran grep audits, OpenAPI diffs, and test suite runs as independent verification passes after each batch.

Opus orchestrated these agents but wrote no implementation code directly. Each phase was planned as a YAML-structured parallelization strategy: tasks with no file dependencies ran simultaneously, and progress was tracked via CLI scripts at approximately 50 tokens per status update rather than through agent round-trips that would have consumed 25,000 tokens each.

The key decision that made parallel execution safe was batching by file ownership. The 15 originally-targeted routers were independent files; each could be migrated by a separate agent simultaneously without merge conflicts. The interface extensions and new ABC creation in the gap-closure phase ran in parallel across separate domain files. Phase 5 (mock repository infrastructure) started as soon as Phase 1 (interface definitions) completed — the mocks only needed the ABC signatures, not the concrete implementations, so test infrastructure was being built concurrently with local repositories.

This is the workflow that lets a single developer move at team velocity. The agents do not get stuck in context-switching, do not lose state between tasks, and do not treat a 9,400-line router file as daunting. They follow the plan, read the file, and apply the pattern. The hard work was in structuring the plan so the pattern was unambiguous at the point of execution.

---

This is why PR `#109` matters even though it shipped nothing visible. It replaced a pattern that would have made every major backend change expensive with one that makes future work additive. The immediate result is a cleaner, more testable API. The larger result is that SkillMeat now has the architectural seam it needs for enterprise storage, authorization, and multi-tenant evolution — and it got there in six days because a well-structured plan and the right delegation model made 82 story points feel like a sprint.