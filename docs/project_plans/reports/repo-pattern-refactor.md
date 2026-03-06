# From Router-Coupled Storage to Repository-First Architecture

**Date**: 2026-03-06
**Author**: GPT 5.4
**Linked Feature**: repo-pattern-refactor-v1
**Related PR**: #109

## Overview

PR `#109` completed one of the most important kinds of engineering work: the kind users do not see directly, but every future feature depends on. The `repo-pattern-refactor` moved SkillMeat’s API away from a model where routers reached straight into the filesystem and SQLite cache, and toward a hexagonal, repository-first design with explicit contracts, dependency injection, and backend replaceability.

Before this work, too much of the storage model leaked upward into the HTTP layer. Routers were doing path resolution, filesystem reads and writes, direct SQLAlchemy work, cache synchronization, and request handling all in the same place. That made the code harder to test, harder to reason about, and expensive to evolve. It also created a serious architectural constraint: any move to enterprise storage, multi-tenant access control, or alternate backends would have required touching router logic all over the API surface.

## Why We Did It

The refactor was driven by a simple architectural requirement: the API needed a stable seam between business behavior and storage behavior. SkillMeat already had a split data model, with the filesystem acting as the source of truth and a SQLite-backed cache serving the web experience. That model worked, but the implementation details were spread across routers in a way that made the system tightly coupled to “local mode.”

The repository pattern solves that by defining storage contracts once, implementing them behind adapters, and letting routers depend on interfaces instead of concrete persistence details. In SkillMeat’s case, that also creates the path for two larger initiatives already planned: request-scoped authorization and future enterprise storage backends. Without this refactor, both of those efforts would have had to fight the codebase instead of building on it.

## What Changed

The first major change was the creation of a dedicated contracts layer in [skillmeat/core/interfaces](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/interfaces). That package now holds the repository interfaces, DTOs, and request context objects that define how the rest of the application talks to storage. This is the architectural boundary: routers and higher-level logic consume stable data contracts instead of ORM models, file handles, or ad hoc query results.

The second change was the introduction of concrete local adapters in [skillmeat/core/repositories](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/core/repositories). These implementations preserve SkillMeat’s existing behavior, including its write-through model where filesystem updates remain authoritative and the cache is synchronized behind the scenes. In other words, the refactor changed the shape of the code, not the product’s local-first behavior.

The third change was wiring the whole system through centralized dependency injection in [skillmeat/api/dependencies.py](/Users/miethe/dev/homelab/development/skillmeat/skillmeat/api/dependencies.py). Instead of routers choosing storage mechanisms themselves, they now ask for repository dependencies. That gives the application one place to decide which implementation to provide, including edition-aware selection for future backends.

From there, the refactor migrated the major API surfaces onto that pattern. What began as a six-repository abstraction expanded into a broader contract surface that now covers core domains like artifacts, projects, collections, deployments, tags, settings, groups, context entities, marketplace sources, and project templates, along with DB-oriented repository helpers for collection and history flows where needed. The important shift is not the exact count of interfaces; it is that storage access now has a defined architectural home.

The work also invested heavily in safety rails. Baseline coverage was added for previously untested routers, mock repositories were introduced for filesystem-free testing, integration tests were expanded around repository behavior, and a pre-refactor OpenAPI snapshot was captured to keep the refactor honest. This was not a “trust the refactor” change. It was a “measure, migrate, and verify” change.

## What It Achieved

The biggest outcome is that SkillMeat is now substantially more adaptable. New storage backends no longer require rewriting router logic. They require implementing repository contracts. That is a fundamental change in the cost of future development.

It also made the API more testable. Mock repositories and DI overrides mean more of the system can be exercised without depending on real filesystem state. That reduces friction for feature work and lowers the risk of regressions in a codebase that was previously forced to test many behaviors through concrete storage.

Just as importantly, the refactor turned architectural intent into policy. SkillMeat now has a documented, repository-first model rather than a loose convention. The design lives in code, not just in aspiration. The key architecture note in [repository-architecture.md](/Users/miethe/dev/homelab/development/skillmeat/.claude/context/key-context/repository-architecture.md) makes that explicit: routers are for HTTP concerns, repositories are for data access, and DTOs are the boundary between them.

This is why PR `#109` matters even though it did not ship a flashy user-facing feature. It replaced a pattern that would have slowed every major backend change with one that compounds engineering leverage. The immediate result is a cleaner, more testable API. The larger result is that SkillMeat now has the architectural seam it needs for enterprise storage, authorization, and future backend evolution without re-litigating persistence decisions in every router.