# CCDash Integration Audit

**Date**: 2026-03-08
**Author**: Codex

CCDash has already implemented the original Agentic SDLC Intelligence foundation on its side. We now need a SkillMeat-focused integration audit to finalize the integration contract and identify any higher-value, fine-tuned integration points.

## Context

- CCDash plan/PRD:
  - /Users/miethe/dev/homelab/development/CCDash/docs/project_plans/PRDs/enhancements/agentic-sdlc-intelligence-foundation-v1.md
  - /Users/miethe/dev/homelab/development/CCDash/docs/project_plans/implementation_plans/enhancements/agentic-sdlc-intelligence-foundation-v1.md

## Goal

Produce the exact SkillMeat-side information needed to:
1. finalize CCDash <-> SkillMeat integration safely,
2. remove remaining assumptions from the current design,
3. identify any additional high-value integrations that would materially improve recommendation quality, workflow matching, context resolution, or deep-link/navigation fidelity.

Please do not speculate. Ground everything in the current SkillMeat codebase and docs. Where something is not yet stable or not yet implemented, say so explicitly.

## Deliverables

1. Integration Contract Summary
Create a concise integration summary covering:
- canonical API base paths and feature flags
- auth model(s) for local vs hosted use
- versioning/stability expectations for external consumers
- pagination/filtering conventions
- error response shapes and retry guidance
- rate limiting / performance considerations if any

2. Canonical Contracts
For each of the following SkillMeat entities, provide the current canonical contract:
- artifacts
- workflows
- context modules
- workflow executions, if relevant
For each one, include:
- list endpoints
- detail endpoints
- relevant query params
- response schema or exact field inventory
- stable IDs and identity rules
- version fields
- provenance/source fields
- whether the contract is considered stable
If an OpenAPI spec exists, point to it. If not, cite the router/schema/model files that currently define the contract.

3. Project/Workspace Mapping
Document the correct way to map a CCDash project to SkillMeat scope:
- project_id
- collection(s)
- workspace
- default collection behavior
- any distinction between filesystem collection, DB collection, and project-scoped workflow/context data
We need the exact recommended mapping strategy for a consumer like CCDash.

4. Artifact Definition Guidance
Clarify the best contract for external consumers resolving artifacts:
- artifact ID format and uniqueness guarantees
- artifact types that CCDash should care about first
- how linked_artifacts should be interpreted
- whether aliases are safe for matching or only primary IDs should be used
- whether tools/metadata/linked artifacts are stable enough for scoring and recommendation use

5. Workflow Definition Guidance
Clarify what CCDash should treat as canonical when working with workflows:
- base workflow definition vs project override
- workflow ID vs name vs persisted DB ID
- stage-level artifact references
- context module references
- execution/planning endpoints that CCDash can safely depend on
- whether there is any stable workflow “plan” output that CCDash should consume directly
- any known caveats around overrides, validation, or execution planning

6. Context Module Guidance
Clarify:
- stable context module identifiers
- whether modules should be resolved by ID or by `ctx:name`
- selector semantics CCDash should know about
- whether module content hashes / packed content / memory membership are available and stable
- whether there is a recommended way to deep-link a context module in the UI

7. Deep-Link / UI Routing Contract
Provide any stable UI route patterns or deep-link conventions for:
- artifact detail pages
- workflow detail pages
- workflow execution pages
- context module pages
If stable UI URLs do not exist, say that explicitly and provide the safest fallback identifiers CCDash should display.

8. Enhancement Opportunities
Identify the highest-value fine-tuned integrations SkillMeat could support for CCDash beyond the current implementation, prioritized by value and difficulty. Examples:
- better project mapping hooks
- explicit workflow recommendation metadata
- stable deep-link IDs/routes
- stack/bundle definitions
- context-pack previews
- workflow outcome metadata
- push/webhook/event integration instead of polling
- override-aware “effective workflow” endpoints
For each opportunity, include:
- why it matters
- whether the current codebase already partially supports it
- the smallest useful change

9. Example Payloads / Fixtures
Provide 2-3 real or sanitized examples for:
- artifact detail payload
- workflow detail payload
- workflow plan payload if available
- context module detail payload
- any execution payload that would help CCDash link recommendations to live SkillMeat state

10. Final Recommendation
End with a “recommended external integration surface for CCDash v1/v2”:
- V1: what CCDash should rely on right now
- V2: what would unlock better fidelity
- Do not include items that are too unstable to recommend

## Output format

- one short summary section
- then sections 1-10 above
- include exact file paths for the router/schema/model/doc sources you used
- clearly mark each item as Confirmed, Partially Confirmed, or Not Yet Stable
