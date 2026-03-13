---
title: "SkillBOM REST API"
description: "REST API reference for Bill of Materials endpoints including generation, verification, and attestation management."
audience: "developers, integration engineers"
tags: ["api", "bom", "attestation", "rest", "endpoints"]
created: "2026-03-13"
updated: "2026-03-13"
category: "API Documentation"
status: "published"
related_documents: ["skillbom-workflow.md", "attestation-compliance.md"]
---

# SkillBOM REST API Reference

Complete REST API documentation for SkillBOM operations.

## Base URL

```
http://localhost:8080/api/v1
```

## Authentication

All `/api/v1/*` endpoints require authentication. Supported methods:

- **Bearer Token** (recommended): `Authorization: Bearer <token>`
- **API Key** (if enabled): `X-API-Key: <key>`
- **Local Auth**: Defaults to `local_admin` in development

## Error Responses

All errors follow a standard format:

```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | Invalid parameters or malformed request |
| `401 Unauthorized` | Authentication failed or missing |
| `404 Not Found` | Resource doesn't exist or caller lacks permission |
| `422 Unprocessable Entity` | Validation error or missing required data |
| `500 Internal Server Error` | Server error (check logs) |

## BOM Endpoints

### GET /bom/snapshot

Retrieve the most recent BOM snapshot for the authenticated user's scope.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | string | null | Optional project scope filter |
| `include_memory_items` | boolean | false | Include memory-item artifacts in response |
| `include_signatures` | boolean | false | Include signature fields in response |

**Response** (200 OK):

```json
{
  "id": 42,
  "project_id": null,
  "commit_sha": null,
  "owner_type": "user",
  "created_at": "2026-03-13T14:30:00Z",
  "bom": {
    "schema_version": "1.0.0",
    "generated_at": "2026-03-13T14:30:00Z",
    "project_path": "/home/user/my-project",
    "artifact_count": 5,
    "artifacts": [
      {
        "name": "frontend-design",
        "type": "skill",
        "source": "anthropics/skills/canvas-design",
        "version": "v2.1.0",
        "content_hash": "abc123def456...",
        "metadata": {
          "author": "Claude Team",
          "description": "Canvas design skill"
        }
      }
    ],
    "metadata": {
      "generator": "skillmeat-bom",
      "elapsed_ms": 245
    }
  },
  "signature": null,
  "signature_algorithm": null,
  "signing_key_id": null
}
```

**Errors**:

- `404 Not Found`: No BOM snapshot exists for the caller's scope

**Example**:

```bash
curl -X GET http://localhost:8080/api/v1/bom/snapshot \
  -H "Authorization: Bearer <token>"
```

---

### POST /bom/generate

Generate a fresh BOM snapshot on demand.

**Authentication**: Required

**Request Body**:

```json
{
  "project_id": null,
  "auto_sign": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `project_id` | string | null | Project scope for filtering. Null generates collection-level BOM |
| `auto_sign` | boolean | false | Sign the generated BOM with default Ed25519 key |

**Response** (201 Created):

```json
{
  "id": 43,
  "project_id": null,
  "owner_type": "user",
  "created_at": "2026-03-13T14:35:00Z",
  "bom": {
    "schema_version": "1.0.0",
    "generated_at": "2026-03-13T14:35:00Z",
    "project_path": "/home/user/my-project",
    "artifact_count": 5,
    "artifacts": [...]
  },
  "signed": true,
  "signature": "abc123def456789...",
  "signing_key_id": "7f8e9d0c1b2a..."
}
```

**Errors**:

- `500 Internal Server Error`: BOM generation failed (check logs)

**Example**:

```bash
curl -X POST http://localhost:8080/api/v1/bom/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": null,
    "auto_sign": true
  }'
```

---

### POST /bom/verify

Verify the cryptographic signature of a BOM snapshot.

**Authentication**: Required

**Request Body**:

```json
{
  "snapshot_id": null,
  "signature": null
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `snapshot_id` | integer | null | BOM snapshot to verify. Null uses the most recent snapshot |
| `signature` | string | null | Hex-encoded signature to verify. Null uses the signature stored in the snapshot |

**Response** (200 OK):

```json
{
  "valid": true,
  "details": "Signature is valid.",
  "key_id": "7f8e9d0c1b2a...",
  "snapshot_id": 42
}
```

| Field | Type | Description |
|-------|------|-------------|
| `valid` | boolean | True if signature is cryptographically valid |
| `details` | string | Human-readable verification result |
| `key_id` | string | SHA-256 fingerprint of the signing key (when available) |
| `snapshot_id` | integer | ID of the snapshot that was verified |

**Errors**:

- `404 Not Found`: Snapshot doesn't exist or caller lacks permission
- `422 Unprocessable Entity`: No signature available or invalid hex encoding

**Example**:

```bash
curl -X POST http://localhost:8080/api/v1/bom/verify \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "snapshot_id": 42
  }'
```

---

## Attestation Endpoints

### GET /attestations

List attestation records with cursor-based pagination.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `owner_scope` | string | null | Filter by `user`, `team`, or `enterprise` |
| `artifact_id` | string | null | Filter by artifact in `type:name` format |
| `limit` | integer | 50 | Maximum records per page (1–200) |
| `cursor` | string | null | Pagination cursor from previous response |

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

**Errors**:

- `400 Bad Request`: Invalid `owner_scope` or cursor

**Pagination**:

```bash
# First page
curl -X GET "http://localhost:8080/api/v1/attestations?limit=50" \
  -H "Authorization: Bearer <token>"

# Next page (using end_cursor from previous response)
curl -X GET "http://localhost:8080/api/v1/attestations?limit=50&cursor=42" \
  -H "Authorization: Bearer <token>"
```

---

### POST /attestations

Create a manual attestation record.

**Authentication**: Required

**Request Body**:

```json
{
  "artifact_id": "skill:payment-processor",
  "owner_scope": null,
  "roles": ["reviewer"],
  "scopes": ["code-review"],
  "visibility": "team",
  "notes": "Passed code review"
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `artifact_id` | string | Yes | — | Artifact in `type:name` format |
| `owner_scope` | string | No | inferred | Override owner scope: `user`, `team`, or `enterprise` |
| `roles` | array | No | [] | RBAC roles (e.g., `["reviewer", "team_admin"]`) |
| `scopes` | array | No | [] | Permission scopes (e.g., `["deploy", "audit"]`) |
| `visibility` | string | No | private | Visibility: `private`, `team`, or `public` |
| `notes` | string | No | null | Free-text notes for offline workflows |

**Response** (201 Created):

```json
{
  "id": "a1b2c3d4e5f6...",
  "artifact_id": "skill:payment-processor",
  "owner_type": "user",
  "owner_id": "u-abc123",
  "roles": ["reviewer"],
  "scopes": ["code-review"],
  "visibility": "team",
  "created_at": "2026-03-13T14:30:00Z"
}
```

**Errors**:

- `400 Bad Request`: Invalid `owner_scope` or `visibility`
- `404 Not Found`: Artifact doesn't exist
- `500 Internal Server Error`: Database error

**Example**:

```bash
curl -X POST http://localhost:8080/api/v1/attestations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "skill:payment-processor",
    "roles": ["security_reviewer"],
    "scopes": ["security-review", "deploy"],
    "visibility": "team"
  }'
```

---

### GET /attestations/{attestation_id}

Retrieve a single attestation record.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `attestation_id` | integer | Attestation record ID |

**Response** (200 OK):

```json
{
  "id": "a1b2c3d4e5f6...",
  "artifact_id": "skill:payment-processor",
  "owner_type": "team",
  "owner_id": "t-team123",
  "roles": ["team_admin"],
  "scopes": ["deploy"],
  "visibility": "team",
  "created_at": "2026-03-13T14:30:00Z"
}
```

**Errors**:

- `404 Not Found`: Record doesn't exist or caller lacks permission

**Example**:

```bash
curl -X GET http://localhost:8080/api/v1/attestations/42 \
  -H "Authorization: Bearer <token>"
```

---

## Data Models

### BOM Schema

Complete structure of a Bill of Materials:

```typescript
interface BomSchema {
  schema_version: string;        // e.g., "1.0.0"
  generated_at: string;          // ISO-8601 timestamp
  project_path?: string;         // Resolved project path
  artifact_count: number;        // Total artifacts
  artifacts: ArtifactEntry[];    // Artifact list
  metadata: Record<string, any>; // Generator metadata
}

interface ArtifactEntry {
  name: string;                  // Artifact name
  type: string;                  // Type (skill, command, etc.)
  source?: string;               // GitHub path or local path
  version?: string;              // Version string
  content_hash: string;          // SHA-256 hex digest
  metadata: Record<string, any>; // Per-type metadata
  members?: Record<string, any>[]; // For composite types
}
```

### Attestation Schema

```typescript
interface AttestationSchema {
  id: string;                    // UUID hex
  artifact_id: string;           // Artifact identifier
  owner_type: string;            // "user", "team", or "enterprise"
  owner_id: string;              // Owner identifier
  roles: string[];               // RBAC roles
  scopes: string[];              // Permission scopes
  visibility: string;            // "private", "team", or "public"
  created_at?: string;           // ISO-8601 timestamp
}
```

---

## Common Workflows

### Generate and Sign a BOM

```bash
# 1. Generate with auto-sign
curl -X POST http://localhost:8080/api/v1/bom/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"auto_sign": true}' > response.json

SNAPSHOT_ID=$(jq -r '.id' response.json)

# 2. Verify the signature
curl -X POST http://localhost:8080/api/v1/bom/verify \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"snapshot_id\": $SNAPSHOT_ID}"
```

### Approve an Artifact for Deployment

```bash
# 1. Create security review attestation
curl -X POST http://localhost:8080/api/v1/attestations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "skill:payment-processor",
    "roles": ["security_reviewer"],
    "scopes": ["security-review"],
    "visibility": "team"
  }'

# 2. Create deployment attestation
curl -X POST http://localhost:8080/api/v1/attestations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "skill:payment-processor",
    "roles": ["deployment_lead"],
    "scopes": ["deploy-production"],
    "visibility": "team"
  }'

# 3. Verify attestations exist
curl -X GET "http://localhost:8080/api/v1/attestations?artifact_id=skill:payment-processor" \
  -H "Authorization: Bearer <token>"
```

### Audit a Deployment

```bash
# Get the BOM from a specific project
curl -X GET "http://localhost:8080/api/v1/bom/snapshot?project_id=my-project" \
  -H "Authorization: Bearer <token>" | jq '.bom.artifacts[]'

# List all attestations for that project's artifacts
for artifact in $(curl -X GET "http://localhost:8080/api/v1/bom/snapshot?project_id=my-project" \
  -H "Authorization: Bearer <token>" | jq -r '.bom.artifacts[].name'); do
  echo "=== Attestations for $artifact ==="
  curl -X GET "http://localhost:8080/api/v1/attestations?artifact_id=skill:$artifact" \
    -H "Authorization: Bearer <token>" | jq '.items[]'
done
```

---

## Rate Limiting

If rate limiting is enabled, responses include rate limit headers:

| Header | Meaning |
|--------|---------|
| `X-RateLimit-Limit` | Max requests per minute |
| `X-RateLimit-Remaining` | Requests remaining in current window |
| `X-RateLimit-Reset` | Unix timestamp when limit resets |

When rate limited (HTTP 429), retry after the `X-RateLimit-Reset` time.

---

## Performance Notes

- **BOM Generation**: Typically 100–500ms depending on artifact count
- **Attestation Queries**: <50ms for typical team sizes
- **Signature Verification**: <10ms (crypto operation)
- **Pagination**: Cursor-based (no offset/limit performance cliff)

---

## SDK/Client Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8080/api/v1"
TOKEN = "<your-token>"

headers = {"Authorization": f"Bearer {TOKEN}"}

# Generate BOM
response = requests.post(
    f"{BASE_URL}/bom/generate",
    headers=headers,
    json={"auto_sign": True}
)
snapshot = response.json()

# Verify signature
response = requests.post(
    f"{BASE_URL}/bom/verify",
    headers=headers,
    json={"snapshot_id": snapshot["id"]}
)
print(response.json()["valid"])

# Create attestation
response = requests.post(
    f"{BASE_URL}/attestations",
    headers=headers,
    json={
        "artifact_id": "skill:my-skill",
        "scopes": ["deploy"],
        "visibility": "team"
    }
)
attestation = response.json()
```

### cURL

See workflow examples above for cURL usage.

### JavaScript/TypeScript

```typescript
const baseUrl = "http://localhost:8080/api/v1";
const token = "<your-token>";

const headers = {
  "Authorization": `Bearer ${token}`,
  "Content-Type": "application/json"
};

// Generate BOM
const genResponse = await fetch(`${baseUrl}/bom/generate`, {
  method: "POST",
  headers,
  body: JSON.stringify({ auto_sign: true })
});
const snapshot = await genResponse.json();

// Verify signature
const verifyResponse = await fetch(`${baseUrl}/bom/verify`, {
  method: "POST",
  headers,
  body: JSON.stringify({ snapshot_id: snapshot.id })
});
const verification = await verifyResponse.json();
console.log(verification.valid);

// Create attestation
const attResponse = await fetch(`${baseUrl}/attestations`, {
  method: "POST",
  headers,
  body: JSON.stringify({
    artifact_id: "skill:my-skill",
    scopes: ["deploy"],
    visibility: "team"
  })
});
const attestation = await attResponse.json();
```

---

## See Also

- [SkillBOM Workflow Guide](../guides/skillbom-workflow.md) — CLI commands and workflows
- [Attestation & Compliance Guide](../guides/attestation-compliance.md) — RBAC, compliance policies, audit trails
