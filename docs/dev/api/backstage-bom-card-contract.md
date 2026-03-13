---
title: "Backstage BOM Card Payload Contract"
description: "Stable payload shape for Backstage EntityPage card consumers and scaffolder actions"
audience: developers
created: 2026-03-13
updated: 2026-03-13
category: "API Documentation"
status: stable
api_version: v1
tags:
  - backstage
  - integration
  - bom
  - payload-contract
related_documents:
  - "docs/dev/api/endpoints/idp-integration.md"
  - "skillmeat/api/schemas/bom.py"
  - "skillmeat/api/routers/idp_integration.py"
---

# Backstage BOM Card Payload Contract

## Overview

The **BOM Card Endpoint** provides a lightweight Bill-of-Materials summary for Backstage EntityPage card renderers and scaffolder actions. This document defines the stable JSON payload contract that Backstage consumers must implement against.

The payload is intentionally compact (omitting full BOM JSON) for efficient consumption in Backstage backend scaffolder actions and frontend card display scenarios.

**Endpoint**: `GET /integrations/idp/bom-card/{project_id}`
**Content-Type**: `application/json`
**Protocol**: HTTP/1.1

---

## Endpoint Reference

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project_id` | string | Yes | Project identifier to fetch the latest BOM snapshot for. Format is backend-specific (typically a catalog-info.yaml project name or UUID). |

### Authentication

**Required Scope**: `artifact:read`

All requests must include valid authentication credentials:

- **Bearer Token**: Include in `Authorization: Bearer <token>` header
- **API Key** (legacy): Include in `X-API-Key: <key>` header (if legacy API key auth is enabled)

When authentication is disabled (development mode), all requests are authorized as `local_admin`.

### Response Codes

| Status | Description |
|--------|-------------|
| **200 OK** | BOM card payload returned successfully. Response body contains the complete `BomCardResponse` object. |
| **404 Not Found** | No BOM snapshot exists for the given `project_id`. Check that at least one BOM has been generated for this project. |
| **401 Unauthorized** | Missing or invalid authentication credentials. Verify token/API key is valid and `artifact:read` scope is granted. |
| **500 Internal Server Error** | Unexpected database query or JSON parsing error. Check server logs for details. |

---

## Response Schema

### BomCardResponse

The complete JSON response shape returned on successful request (HTTP 200).

```typescript
interface BomCardResponse {
  // Identifiers
  project_id: string;
  snapshot_id: number;

  // Metadata
  generated_at: string;      // ISO-8601 UTC timestamp
  artifact_count: number;    // >= 0
  attestation_count: number; // >= 0
  signature_status: string;  // "signed" | "unsigned"

  // Payload
  artifacts: BomCardArtifactEntry[];
}
```

### BomCardArtifactEntry

Lightweight artifact summary included in the `artifacts` array.

```typescript
interface BomCardArtifactEntry {
  name: string;           // Artifact name (unique within type)
  type: string;           // Artifact type (e.g., "skill", "command", "agent")
  version: string | null; // Deployed or upstream version; null if not set
  content_hash: string;   // SHA-256 hex digest; empty string if unavailable
}
```

---

## Field Reference

### Top-Level Fields

#### `project_id`

- **Type**: `string`
- **Nullable**: No
- **Description**: Project identifier matching the path parameter. Used by Backstage to correlate BOM data with catalog metadata.
- **Example**: `"my-project"`, `"3e4f5c6d-7a8b-9c0d-e1f2-3a4b5c6d7e8f"`

#### `snapshot_id`

- **Type**: `number` (integer)
- **Nullable**: No
- **Description**: Primary key of the `BomSnapshot` database row. Unique identifier for this snapshot version.
- **Use Case**: Scaffolder actions can use `snapshot_id` to track which BOM generation run they're referencing for reproducibility or logging.
- **Example**: `42`, `1001`

#### `generated_at`

- **Type**: `string` (ISO-8601 UTC timestamp)
- **Nullable**: No
- **Format**: `YYYY-MM-DDTHH:mm:ss.sssZ` or `YYYY-MM-DDTHH:mm:ssZ`
- **Description**: Timestamp when the BOM snapshot was generated/captured. Always in UTC.
- **Use Case**: Backstage cards can display staleness ("Last updated 2 hours ago").
- **Example**: `"2026-03-13T14:32:00Z"`

#### `artifact_count`

- **Type**: `number` (integer >= 0)
- **Nullable**: No
- **Description**: Total number of artifact entries present in the `artifacts` array. Useful for validation and UI summary ("12 artifacts").
- **Example**: `12`, `0`

#### `attestation_count`

- **Type**: `number` (integer >= 0)
- **Nullable**: No
- **Description**: Number of `AttestationRecord` rows in the database linked to artifacts present in this snapshot. Reflects the attestation coverage across the BOM.
- **Calculation**: Counts all `AttestationRecord` rows where `artifact_id` matches any artifact's `type:name` identifier in the snapshot.
- **Use Case**: Backstage cards can display attestation coverage ("8/12 artifacts attested").
- **Example**: `8`, `0`

#### `signature_status`

- **Type**: `string`
- **Nullable**: No
- **Enum**: `"signed"` | `"unsigned"`
- **Description**: Cryptographic signature status of the BOM snapshot.
  - `"signed"`: Snapshot carries a valid digital signature (future capability).
  - `"unsigned"`: Snapshot is not signed (current state).
- **Use Case**: Backstage security cards can display trust indicators. In future, `"signed"` enables supply-chain verification workflows.
- **Example**: `"unsigned"`

#### `artifacts`

- **Type**: `BomCardArtifactEntry[]`
- **Nullable**: No (array may be empty)
- **Description**: Lightweight artifact summaries from the snapshot. Sorted by `(type, name)` tuples.
- **Minimum**: `0` artifacts (empty array if no artifacts in BOM)
- **Maximum**: Unbounded, but typically < 500 per snapshot

---

### Artifact Entry Fields

#### `name`

- **Type**: `string`
- **Nullable**: No
- **Description**: Artifact name, unique within its type. Combined with `type` to form the artifact identifier (`type:name`).
- **Example**: `"frontend-design"`, `"oauth2-handler"`

#### `type`

- **Type**: `string`
- **Nullable**: No
- **Description**: Artifact type classification. All 13+ artifact types are supported.
- **Known Types**: `"skill"`, `"command"`, `"agent"`, `"hook"`, `"mcp"`, `"deployment_set"`, `"composite"`, and others.
- **Example**: `"skill"`, `"command"`

#### `version`

- **Type**: `string | null`
- **Nullable**: Yes
- **Description**: Deployed or upstream version string. Reflects the version of the artifact included in the BOM.
- **Examples**: `"1.2.0"`, `"v0.0.1"`, `"latest"`, `null`
- **Parsing**: Frontend consumers should not attempt to parse version strings; treat as opaque identifiers.

#### `content_hash`

- **Type**: `string`
- **Nullable**: No
- **Description**: SHA-256 hexadecimal digest of the artifact content. Enables content-based deduplication and integrity verification.
- **Empty Case**: May be empty string (`""`) if hash is unavailable at generation time.
- **Example**: `"abc123def456..."` (64 hex characters), `""`

---

## Example Payloads

### Complete Example (Full BOM)

A realistic BOM card with multiple artifact entries and attestations.

```json
{
  "project_id": "my-api-project",
  "snapshot_id": 42,
  "generated_at": "2026-03-13T14:32:00Z",
  "artifact_count": 4,
  "attestation_count": 3,
  "signature_status": "unsigned",
  "artifacts": [
    {
      "name": "auth-handler",
      "type": "skill",
      "version": "1.2.0",
      "content_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    },
    {
      "name": "database-schema",
      "type": "command",
      "version": null,
      "content_hash": "5d41402abc4b2a76b9719d911017c592"
    },
    {
      "name": "api-router",
      "type": "composite",
      "version": "0.5.0-beta",
      "content_hash": "356a192b7913b04c54574d18c28d46e6395428ab"
    },
    {
      "name": "deployment-hook",
      "type": "hook",
      "version": "latest",
      "content_hash": ""
    }
  ]
}
```

**Interpretation**:
- Project `"my-api-project"` has 4 artifacts in the latest BOM snapshot.
- 3 artifacts have attestation records; 1 does not.
- Snapshot was generated at 2026-03-13 14:32 UTC.
- All artifacts include valid content hashes except `deployment-hook`.

### Minimal Example (Empty BOM)

An edge-case BOM with no artifacts or attestations (e.g., project just created).

```json
{
  "project_id": "new-project",
  "snapshot_id": 1,
  "generated_at": "2026-03-13T10:00:00Z",
  "artifact_count": 0,
  "attestation_count": 0,
  "signature_status": "unsigned",
  "artifacts": []
}
```

**Interpretation**:
- Project `"new-project"` has no artifacts deployed yet.
- The snapshot row exists but the BOM is empty.
- Backstage cards should gracefully render empty state.

### Mixed Versions Example

Artifacts with various version string formats (real-world scenario).

```json
{
  "project_id": "monorepo-project",
  "snapshot_id": 87,
  "generated_at": "2026-03-13T15:45:30Z",
  "artifact_count": 3,
  "attestation_count": 2,
  "signature_status": "unsigned",
  "artifacts": [
    {
      "name": "cli-tool",
      "type": "skill",
      "version": "v2.1.0",
      "content_hash": "abcdef0123456789"
    },
    {
      "name": "web-ui",
      "type": "composite",
      "version": "202603-release",
      "content_hash": "fedcba9876543210"
    },
    {
      "name": "background-worker",
      "type": "agent",
      "version": null,
      "content_hash": "1111111111111111"
    }
  ]
}
```

**Interpretation**:
- Demonstrates variety of version formats (semver, custom date, null).
- 2 artifacts are attested out of 3.
- Content hashes are all populated (non-empty).

---

## Versioning Strategy

### Payload Version

The BOM card payload does not currently include an explicit `version` or `schema_version` field. All consumers must assume the shape documented here.

### Future Compatibility

When payload evolution becomes necessary, we will:

1. **Add a `schema_version` field** to the root response object
2. **Increment on breaking changes** (field removal, type change)
3. **Maintain backward compatibility** where possible (new optional fields, new artifact types)
4. **Provide migration guidance** for Backstage consumers

**Current schema version** (implicit): `1.0.0`

### Artifact Type Evolution

New artifact types may be added in future SkillMeat releases. Consumers must gracefully handle unknown types:

```typescript
// Good: Treat unknown types as opaque
artifacts.forEach(a => {
  console.log(`${a.type}:${a.name}`); // Works for any type
});

// Bad: Assume closed set of types
if (a.type === 'skill') { /* ... */ }  // Breaks when new types appear
```

---

## Consumer Integration Notes

### Backstage Backend Scaffolder Actions

The `BomCardResponse` payload is designed for consumption by Backstage scaffolder actions that need to:

- List available artifacts in a project
- Check artifact versions before scaffold generation
- Validate artifact availability before deployment

**Typical usage**:

```typescript
// In a Backstage scaffolder action
const bomCard = await fetch(
  `${API_URL}/integrations/idp/bom-card/${projectId}`,
  { headers: { Authorization: `Bearer ${token}` } }
).then(r => r.json());

// Scaffold generation can now reference artifact versions
const selectedArtifact = bomCard.artifacts.find(a => a.name === targetName);
if (!selectedArtifact) {
  throw new Error(`Artifact not found in BOM`);
}
```

### Backstage EntityPage Cards

Frontend cards rendering BOM metadata should:

- Display `artifact_count` and `attestation_count` summaries
- Show `generated_at` timestamp with staleness indicator
- List artifact names and types in a compact UI
- (Future) Leverage `signature_status` for trust indicators

---

## Error Response Format

While the contract defines the 200 response, error responses follow this pattern:

```json
{
  "detail": "No BOM snapshot found for project 'unknown-project'"
}
```

**404 Example**:
```json
{
  "detail": "No BOM snapshot found for project 'unknown-project'"
}
```

**401 Example** (authentication missing):
```json
{
  "detail": "Not authenticated"
}
```

**500 Example** (database error):
```json
{
  "detail": "Failed to query BOM snapshot"
}
```

---

## Implementation Notes

### Server-Side (SkillMeat API)

The endpoint implementation in `skillmeat/api/routers/idp_integration.py`:

1. **Queries** the `bom_snapshots` table for the most recent row matching `project_id`
2. **Parses** the stored `bom_json` JSON string
3. **Extracts** lightweight artifact metadata (name, type, version, content_hash)
4. **Counts** `AttestationRecord` rows linked to artifacts in the snapshot
5. **Determines** signature status from `snapshot.signature` field
6. **Returns** a populated `BomCardResponse` object

### Client-Side (Backstage or other consumers)

1. **Make authenticated request** to the endpoint with valid `artifact:read` scope
2. **Handle 404** gracefully (project may not have a BOM yet)
3. **Parse response** as `BomCardResponse` JSON
4. **Validate** that all required fields are present (defensive programming)
5. **Update cache/UI** with artifact metadata

### Content Hash Validation

Content hashes are provided for integrity verification but not validation in the current release. Consumers may use them for:

- Deduplication detection (same `content_hash` = identical artifact)
- Change detection across BOM versions
- Future supply-chain provenance workflows

---

## Related Documentation

- **Endpoint Implementation**: `skillmeat/api/routers/idp_integration.py` — `get_bom_card()` function
- **Schema Definitions**: `skillmeat/api/schemas/bom.py` — `BomCardResponse`, `BomCardArtifactEntry` Pydantic models
- **BOM Database Model**: `skillmeat/cache/models.py` — `BomSnapshot` ORM model
- **Backstage Integration Guide**: `.../docs/integrations/backstage.md` (future reference)
