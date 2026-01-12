---
description: Perform comprehensive SPIKE research and design with domain experts and ADR documentation
allowed-tools: Read(./**), Write(./**), Edit, MultiEdit, Glob, Grep, Bash
argument-hint: "[document-path-or-feature-description]"
---

Execute comprehensive SPIKE for "$ARGUMENTS" using MP architecture patterns:

<!-- MeatyCapture Integration - Project: skillmeat -->
## Phase 0: Discovery

Search request-logs for related items to inform the SPIKE:
- `/mc search "spike-keyword" skillmeat` - Find related bugs/enhancements
- `/mc search "type:enhancement" skillmeat` - Find enhancements that may inform scope

## Phase 1: Input Analysis & Scope Definition

1. **Analyze Input Source**
   - If path provided: Read document and extract requirements
   - If description: Capture feature scope and objectives
   - Identify affected MP layers: UI → API → Database → Infrastructure

2. **Initial Domain Assessment**
   - Classify feature type: UI/UX, Backend, Full-stack, Infrastructure
   - Identify required specialists: Architect, Designer, Database, Security
   - Map to existing MP patterns and potential conflicts

## Phase 2: Domain Research with Specialists

3. **Technical Research (Use architect agent)**
   ```bash
   # Spawn architect agent for technical analysis
   ```
   - Analyze technical requirements and constraints
   - Review MP architecture compliance (routers → services → repos → DB)
   - Identify integration points and dependencies
   - Research technology stack implications

4. **UI/UX Design (Use designer agent if UI components needed)**
   ```bash
   # Spawn designer agent for user experience
   ```
   - Create user flow and interaction patterns
   - Design component specifications for @meaty/ui
   - Define accessibility requirements
   - Plan responsive behavior and states

5. **Database Design (Use database agent if data layer changes)**
   ```bash
   # Spawn database agent for data modeling
   ```
   - Design schema changes with RLS patterns
   - Plan migration strategy with Alembic
   - Analyze performance and indexing requirements
   - Review data access patterns and repositories

6. **Security Analysis (Use security agent for auth/permissions)**
   ```bash
   # Spawn security agent for security review
   ```
   - Review authentication and authorization flows
   - Analyze RLS policy requirements
   - Identify potential security vectors
   - Plan OWASP compliance measures

## Phase 3: Design Integration & Documentation

7. **Create Technical Design Document**
   ```markdown
   # SPIKE: [Feature Name]

   ## Executive Summary
   [High-level overview and business value]

   ## Requirements Analysis
   [Functional and non-functional requirements]

   ## Architecture Design
   ### MP Layer Impact
   - **UI Layer**: [Component changes and new primitives]
   - **API Layer**: [Router/service/repository changes]
   - **Database Layer**: [Schema changes and migrations]
   - **Infrastructure**: [Deployment and configuration changes]

   ### Integration Points
   [How this integrates with existing MP architecture]

   ## Implementation Plan
   ### Phase 1: Foundation
   [Database, core services, DTOs]

   ### Phase 2: API Layer
   [Routes, validation, error handling]

   ### Phase 3: Frontend
   [UI components, hooks, integration]

   ### Phase 4: Testing & Observability
   [Test coverage, telemetry, monitoring]

   ## Open Questions
   [Unresolved technical decisions]

   ## Risk Assessment
   [Technical and business risks with mitigations]
   ```

8. **Generate Architecture Decision Records (ADRs)**
   - Create ADRs for significant technical decisions
   - Document alternatives considered and rationale
   - Follow MP ADR template in `/docs/architecture/ADRs/`

9. **Update Project Documentation**
   - Link to relevant existing documentation
   - Update architecture diagrams if needed
   - Create OpenAPI spec updates for API changes

## Phase 4: Implementation Planning

10. **Create Implementation Checklist**
    - Break down into MP architecture sequence: schema → DTO → repo → service → API → UI → tests
    - Estimate complexity and dependencies
    - Identify required MP infrastructure updates
    - Plan observability integration (spans, logs, metrics)

11. **Define Acceptance Criteria**
    - Functional acceptance criteria
    - Performance requirements
    - Security acceptance criteria
    - Accessibility compliance (WCAG 2.1 AA)

## Phase 5: Output Generation

12. **Generate SPIKE Documentation Package**
    Create comprehensive documentation in `/docs/spikes/`:
    - Technical design document
    - Implementation plan with timeline estimates
    - ADRs for major decisions
    - Open questions and assumptions
    - Risk assessment and mitigation strategies

13. **Create Implementation Commands**
    Generate follow-up commands for implementation phases:
    - Database migration commands
    - API development commands
    - UI component creation commands
    - Testing strategy commands

## Deliverables

The SPIKE will produce:
- **Technical Design Document** (`/docs/spikes/[feature-name]-spike.md`)
- **ADRs** (`/docs/architecture/ADRs/[decision-topic].md`)
- **Implementation Plan** with phased approach following MP patterns
- **Open Questions Log** for future research
- **Risk Assessment** with mitigation strategies
- **Follow-up Commands** for implementation phases

## MP Architecture Compliance

Ensure all designs follow:
- **Layered Architecture**: Routers → Services → Repositories → DB
- **Error Handling**: ErrorResponse envelopes throughout
- **Pagination**: Cursor-based pagination for lists
- **Authentication**: Clerk integration with RLS
- **UI Consistency**: @meaty/ui components only
- **Observability**: OpenTelemetry spans and structured logging
- **Testing**: Unit/integration/E2E with accessibility checks

Follow @CLAUDE.md implementation sequence exactly.
Reference architecture patterns from @web-architecture-refactor-v1.md.
Use @DESIGN-GUIDE.md for UI component specifications.
