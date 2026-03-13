---
title: "Attestation & Compliance Guide"
description: "Guide to managing attestations, RBAC scoping, compliance workflows, and audit trails for SkillBOM artifacts."
audience: "developers, operators, compliance teams"
tags: ["attestation", "rbac", "compliance", "audit", "visibility"]
created: "2026-03-13"
updated: "2026-03-13"
category: "Guides"
status: "published"
related_documents: ["skillbom-workflow.md", "bom-api.md"]
---

# Attestation & Compliance Guide

This guide covers attestations—records linking artifacts to owners with role-based access control—and how to use them for compliance and audit workflows.

## What is an Attestation?

An attestation is a record that asserts: "Entity X (user/team/organization) takes responsibility for artifact Y and grants the following permissions/scopes."

Each attestation record contains:

- **Artifact ID**: The artifact being attested (e.g., `skill:frontend-design`)
- **Owner**: Who made the attestation (user, team, or enterprise)
- **Roles**: RBAC roles held by this attestation (e.g., `team_admin`, `reviewer`)
- **Scopes**: Permission scopes covered (e.g., `deploy`, `audit`, `security-review`)
- **Visibility**: Who can see this attestation (`private`, `team`, `public`)
- **Timestamp**: When the attestation was created

Attestations serve two purposes:

1. **Proof of Intent**: "We have reviewed and approved this artifact"
2. **Access Control**: "These scopes are granted to this principal for this artifact"

## RBAC Scoping

SkillBOM enforces a role hierarchy for visibility and access decisions. Higher roles inherit lower privileges.

### Role Hierarchy (Most → Least Privileged)

| Role | Level | Permissions |
|------|-------|-------------|
| `system_admin` | 5 | See all attestations; unrestricted access across tenants |
| `enterprise_admin` | 4 | See all enterprise-scoped attestations |
| `team_admin` | 3 | Manage attestations for their team; see all team records |
| `team_member` | 2 | See non-private team attestations |
| `viewer` | 1 | See only their own attestations (+ public ones) |

### Ownership Precedence

When determining the owner of a resource, precedence is evaluated as:

1. **Enterprise** (if `tenant_id` is set) — highest priority
2. **Team** (if `team_id` is set)
3. **User** (if `user_id` is set)
4. **Anonymous** (fallback when no IDs provided)

### Visibility Levels

Attestations can be marked with three visibility levels that interact with roles:

| Visibility | Behavior |
|------------|----------|
| `private` | Only the owner can view |
| `team` | Team members and above can view |
| `public` | Any authenticated user can view |

**Visibility + Role Decision Table**:

| Record Owner | Viewer's Role | Visibility | Visible? | Why |
|---|---|---|---|---|
| User A | User A | private | ✓ | Owner match |
| User A | User B | private | ✗ | Different owner, private |
| User A | Team admin of User's team | private | ✗ | Team context doesn't apply to user records |
| Team T | Team T member | team | ✓ | Team match + non-private visibility |
| Team T | Team T member | private | ✗ | Team match but private visibility |
| Team T | Enterprise admin | team | ✓ | Enterprise admin sees all enterprise records |
| Any | Anyone | public | ✓ | Public is visible to all authenticated users |

## Compliance Use Cases

### 1. Deployment Approval Workflow

Require attestations from security and deployment teams before production deployment:

```bash
# Team lead creates attestation asserting security review passed
curl -X POST http://localhost:8080/api/v1/attestations \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "skill:payment-processor",
    "roles": ["security_reviewer"],
    "scopes": ["security-review", "deploy"],
    "visibility": "team"
  }'
```

Deployment pipeline verifies that all required attestations exist before proceeding.

### 2. Multi-Stage Release Gating

Track different approval stages using attestation scopes:

```bash
# Development: code review scope
{
  "artifact_id": "command:build-script",
  "roles": ["code_reviewer"],
  "scopes": ["code-review"],
  "visibility": "team"
}

# Staging: performance testing scope
{
  "artifact_id": "command:build-script",
  "roles": ["qa_engineer"],
  "scopes": ["performance-test", "deploy-staging"],
  "visibility": "team"
}

# Production: final approval scope
{
  "artifact_id": "command:build-script",
  "roles": ["release_manager"],
  "scopes": ["deploy-production"],
  "visibility": "team"
}
```

### 3. Compliance Policy Enforcement

Enterprise deployments can define required attestation policies:

- "All skills must have a security attestation before deployment"
- "Commands in the financial domain require audit-trail attestation"
- "External API integrations require legal review"

The policy enforcer checks that all required scopes are covered by existing attestations.

### 4. Audit Trail Analysis

Combine attestations with BOM snapshots to create an immutable audit trail:

1. Artifact deployed → BOM generated
2. Security team attests → attestation record created
3. Commit made → Git hook links BOM to commit with `SkillBOM-Hash` footer
4. Later audit → review Git history + attestations to verify approval workflow was followed

## Audit Trail Analysis

### Reconstructing a Deployment Decision

Given a Git commit, reconstruct what was deployed and who approved it:

```bash
# 1. Get the BOM from the commit
git show <commit>:artifact_metadata.json | jq '.bom'

# 2. Query attestations for the artifacts in that BOM
curl "http://localhost:8080/api/v1/attestations?artifact_id=skill:payment-processor"

# 3. Cross-reference timestamps
# - BOM generated_at
# - Attestations created_at
# - Ensure attestations predate deployment
```

### Compliance Reports

Generate compliance reports by querying attestation data:

```bash
# List all attestations with "security-review" scope
curl "http://localhost:8080/api/v1/attestations?scopes=security-review"

# Aggregate across team
curl "http://localhost:8080/api/v1/attestations?owner_scope=team&team_id=t-123"

# Timeline: sort by created_at to show approval sequence
```

## Practical Workflows

### Approving an Artifact for Production

**Step 1: Security Review**

```bash
# Security team member creates attestation
curl -X POST http://localhost:8080/api/v1/attestations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "skill:payment-processor",
    "roles": ["security_reviewer"],
    "scopes": ["security-review"],
    "visibility": "team"
  }'
```

**Step 2: Deployment Lead Approval**

```bash
# Deployment lead creates final attestation
curl -X POST http://localhost:8080/api/v1/attestations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "skill:payment-processor",
    "roles": ["deployment_lead"],
    "scopes": ["deploy-production"],
    "visibility": "team"
  }'
```

**Step 3: Generate BOM & Deploy**

```bash
# Generate signed BOM (snapshot of approved state)
skillmeat bom generate --auto-sign

# Deploy via CI/CD (which verifies attestations)
./scripts/deploy-production.sh
```

### Handling Revoked Approval

If an issue is discovered and approval needs to be revoked:

1. Do NOT delete the attestation (audit trail preservation)
2. Create a new attestation with a `revoked` scope or special visibility
3. Update deployment policy to check for revocation markers
4. Document the reason in your Git commit message

### Cross-Team Collaboration

For organizations with multiple teams:

```bash
# Team A creates attestation visible only to their team
{
  "artifact_id": "command:shared-build-tool",
  "owner_scope": "team",  # Their team
  "roles": ["team_admin"],
  "scopes": ["tested", "stable"],
  "visibility": "team"
}

# Team B can see this because they're in the same org (enterprise)
# Enterprise admin can see all team attestations
```

## Database Schema

Attestations are stored in the `attestation_records` table:

| Field | Type | Meaning |
|-------|------|---------|
| `id` | UUID | Unique attestation identifier |
| `artifact_id` | String | Artifact being attested (e.g., `skill:name`) |
| `owner_type` | String | `user`, `team`, or `enterprise` |
| `owner_id` | String | Identifier of the owner |
| `roles` | Array | RBAC roles (e.g., `["team_admin", "reviewer"]`) |
| `scopes` | Array | Permission scopes (e.g., `["deploy", "audit"]`) |
| `visibility` | String | `private`, `team`, or `public` |
| `created_at` | Timestamp | ISO-8601 creation time |

## API Reference

### Create Attestation

```bash
POST /api/v1/attestations
```

**Request body**:

```json
{
  "artifact_id": "skill:payment-processor",
  "owner_scope": "user",
  "roles": ["reviewer"],
  "scopes": ["code-review", "security-review"],
  "visibility": "team",
  "notes": "Passed SAST scanning and manual review"
}
```

**Response** (201 Created):

```json
{
  "id": "a1b2c3d4e5f6...",
  "artifact_id": "skill:payment-processor",
  "owner_type": "user",
  "owner_id": "u-abc123",
  "roles": ["reviewer"],
  "scopes": ["code-review", "security-review"],
  "visibility": "team",
  "created_at": "2026-03-13T14:30:00Z"
}
```

### List Attestations

```bash
GET /api/v1/attestations?owner_scope=team&artifact_id=skill:payment-processor&limit=50&cursor=<cursor>
```

**Query parameters**:

- `owner_scope` (optional): Filter by `user`, `team`, or `enterprise`
- `artifact_id` (optional): Filter by artifact
- `limit` (default: 50, max: 200): Page size
- `cursor` (optional): Pagination cursor

**Response** (200 OK):

```json
{
  "items": [
    {
      "id": "a1b2c3d4e5f6...",
      "artifact_id": "skill:payment-processor",
      "owner_type": "team",
      "owner_id": "t-team123",
      "roles": ["team_admin"],
      "scopes": ["deploy", "audit"],
      "visibility": "team",
      "created_at": "2026-03-13T14:30:00Z"
    }
  ],
  "page_info": {
    "end_cursor": "42",
    "has_next_page": false
  }
}
```

### Get Single Attestation

```bash
GET /api/v1/attestations/{attestation_id}
```

**Response** (200 OK): Same as Create response

**Errors**:
- `404 Not Found`: Record doesn't exist or caller lacks permission
- `401 Unauthorized`: Not authenticated

## Compliance Enforcement

SkillBOM includes a policy enforcement engine that validates attestation coverage:

### Policy Definition (Enterprise)

```python
# In enterprise edition, policies define requirements
policy = AttestationPolicy(
    name="Production Deployment Policy",
    required_artifacts=["skill:payment-processor", "skill:billing-sync"],
    required_scopes=["security-review", "deploy-production"],
    tenant_id="enterprise-id"
)
```

### Compliance Validation

```python
from skillmeat.core.bom.policy import AttestationPolicyEnforcer

enforcer = AttestationPolicyEnforcer(is_enterprise=True)
report = enforcer.evaluate_full_compliance(
    policy=policy,
    attested_artifact_ids=[...],
    attestation_records=[...]
)

print(f"Compliant: {report.is_compliant}")
print(f"Missing artifacts: {report.artifact_validation.missing}")
print(f"Missing scopes: {report.scope_validation.missing}")
```

## Best Practices

1. **Create attestations for every approval stage**: Code review → Security review → Deployment approval
2. **Use scopes granularly**: Different scopes for different concerns (deploy, audit, security-review)
3. **Prefer `team` visibility**: Allows team collaboration while maintaining privacy from other teams
4. **Document in Git**: Reference attestation IDs in commit messages for traceability
5. **Audit regularly**: Run attestation reports monthly to verify compliance
6. **Archive old attestations**: Don't delete; mark with `archived` scope or move to audit storage
7. **Test policies locally**: Use `is_enterprise=False` mode during development (always permissive)

## Troubleshooting

### "Attestation not found" when creating deployment

**Problem**: API returns 404 when checking attestations.

**Solution**: Verify the artifact_id format is `type:name` (e.g., `skill:my-skill`).

### Visibility not working as expected

**Problem**: Team member can see private attestations from their team.

**Cause**: Check if the user has elevated roles (team_admin). Admins can see all team records regardless of visibility.

**Solution**: Use more granular role-based filtering in your compliance checks.

### Attestations visible across teams

**Problem**: Users from Team A can see Team B's attestations.

**Cause**: Attestations are likely marked with `visibility=public` or user has enterprise admin role.

**Solution**: Change visibility to `team` or review user roles.

## See Also

- [SkillBOM Workflow Guide](skillbom-workflow.md) — CLI and workflow patterns
- [BOM API Documentation](../api/bom-api.md) — REST API reference
- [Rollout Plan](../ops/rollout-plan.md) — Feature flag and gradual rollout strategy
