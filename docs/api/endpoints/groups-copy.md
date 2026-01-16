---
title: Copy Group Endpoint
description: API documentation for the copy group endpoint - copying artifact groups between collections
audience: developers
tags: [api, groups, collections, endpoints]
created: 2025-01-16
updated: 2025-01-16
category: API Endpoints
status: documented
related_documents:
  - docs/api/groups-overview.md
  - docs/api/endpoints/groups-create.md
  - docs/api/endpoints/collections-overview.md
---

# Copy Group Endpoint

## Overview

The copy group endpoint allows you to duplicate a group (with all its artifacts) from one collection to another. This is useful for reusing group structures across multiple collections or creating templates.

**Endpoint**: `POST /api/v1/groups/{group_id}/copy`

**Status Code**: `201 Created`

**Authentication**: Not explicitly required (depends on authentication middleware)

---

## Request

### Path Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `group_id` | string | Yes | The ID of the source group to copy |

### Request Body

```typescript
interface CopyGroupRequest {
  target_collection_id: string;  // ID of the destination collection
}
```

**Body Parameters**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `target_collection_id` | string | Yes | ID of the collection where the group will be copied to |

### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/groups/group-123/copy" \
  -H "Content-Type: application/json" \
  -d {
    "target_collection_id": "another-collection-456"
  }
```

```typescript
// TypeScript/JavaScript using Fetch API
const response = await fetch('/api/v1/groups/group-123/copy', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    target_collection_id: 'another-collection-456',
  }),
});

const newGroup = await response.json();
console.log(`Created group: ${newGroup.id} (${newGroup.name})`);
```

```python
# Python using requests
import requests

response = requests.post(
    'http://localhost:8000/api/v1/groups/group-123/copy',
    json={
        'target_collection_id': 'another-collection-456'
    }
)

new_group = response.json()
print(f"Created group: {new_group['id']} ({new_group['name']})")
```

---

## Response

### Success Response (201 Created)

Returns the newly created group in the target collection with the same structure as `GroupResponse`.

```typescript
interface GroupResponse {
  id: string;                    // Unique identifier for the new group
  collection_id: string;         // ID of the target collection
  name: string;                  // Original name + " (Copy)" suffix
  description: string | null;    // Same description as source group
  position: int;                 // Position in target collection (appended)
  artifact_count: int;           // Number of artifacts in the new group
  created_at: string;            // ISO 8601 creation timestamp
  updated_at: string;            // ISO 8601 update timestamp
}
```

### Success Example

```json
{
  "id": "new-group-789",
  "collection_id": "another-collection-456",
  "name": "Frontend Development (Copy)",
  "description": "Skills and tools for frontend development",
  "position": 2,
  "artifact_count": 5,
  "created_at": "2025-01-16T10:30:00Z",
  "updated_at": "2025-01-16T10:30:00Z"
}
```

### Error Responses

#### 404 Not Found

Returned when the source group or target collection does not exist.

```json
{
  "detail": "Group 'invalid-group-id' not found"
}
```

OR

```json
{
  "detail": "Target collection 'invalid-collection-id' not found"
}
```

#### 400 Bad Request

Returned when the group name already exists in the target collection.

```json
{
  "detail": "Group 'Frontend Development (Copy)' already exists in target collection"
}
```

#### 422 Unprocessable Entity

Returned when the request body is invalid (missing required field, wrong type, etc.).

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "target_collection_id"],
      "msg": "Field required"
    }
  ]
}
```

#### 500 Internal Server Error

Returned when an unexpected database or server error occurs.

```json
{
  "detail": "Failed to copy group"
}
```

---

## Behavior Details

### Naming Convention

The copied group is automatically renamed with a " (Copy)" suffix appended to the original name:

- Source group: `"Frontend Development"`
- Copied group: `"Frontend Development (Copy)"`

### Artifact Handling

When copying a group, all artifacts are copied with the following logic:

1. **Artifacts already in target collection**: These artifacts are added to the new group by reference (no duplication)
2. **Artifacts not in target collection**: These artifacts are first added to the target collection, then added to the new group
3. **Position preservation**: Artifacts maintain their relative order from the source group

### Position in Collection

The new group is automatically positioned at the end of the target collection:

- If target collection has 3 groups (positions 0, 1, 2), new group gets position 3
- If target collection is empty, new group gets position 0

### Description Copy

The group description is copied exactly as it appears in the source group. If the source group has no description, the copied group will also have no description.

---

## Use Cases

### 1. Duplicate Group Within Organization

Copy a well-organized group to another collection so multiple teams can use similar structures:

```typescript
// Copy "Web Development Tools" to another team's collection
const response = await fetch('/api/v1/groups/web-dev-tools/copy', {
  method: 'POST',
  body: JSON.stringify({
    target_collection_id: 'team-b-collection'
  })
});
```

### 2. Create Group Templates

Use a template collection to store standard group structures, then copy them to new collections:

```typescript
// Copy "Database Management Tools" template
const response = await fetch('/api/v1/groups/db-template-group/copy', {
  method: 'POST',
  body: JSON.stringify({
    target_collection_id: 'new-project-collection'
  })
});
```

### 3. Backup or Archive Groups

Create copies of important groups in an archive collection:

```typescript
// Backup critical group to archive
await fetch('/api/v1/groups/critical-tools/copy', {
  method: 'POST',
  body: JSON.stringify({
    target_collection_id: 'archive-2025'
  })
});
```

---

## Important Notes

### Name Conflict Handling

If a group with the copied name already exists in the target collection, the operation will fail with a `400 Bad Request` error. In this case:

1. Delete the conflicting group first, OR
2. Manually rename the target group after copying, OR
3. Ensure the source group name is unique in the target collection

### Transaction Atomicity

The copy operation is fully atomic:
- Either all artifacts are copied and the group is created, OR
- Nothing changes (on any error)

No partial copies will be created.

### Performance Considerations

- Large groups with many artifacts may take longer to copy
- The operation locks the target collection during copying to maintain consistency
- For very large groups (100+ artifacts), consider copying during low-traffic periods

---

## Related Operations

### Create a New Group

Create a group without copying:
```
POST /api/v1/groups
```

### Update a Group

Modify group metadata after copying:
```
PUT /api/v1/groups/{group_id}
```

### Delete a Group

Remove a copied group:
```
DELETE /api/v1/groups/{group_id}
```

### List Groups in Collection

See all groups including copied ones:
```
GET /api/v1/groups?collection_id={collection_id}
```

### Get Group Details

View the copied group's artifacts:
```
GET /api/v1/groups/{group_id}
```

---

## Implementation Notes (For Developers)

### Database Operations

The endpoint performs these operations in a single transaction:

1. Verify source group exists
2. Verify target collection exists
3. Create new group with " (Copy)" suffix
4. Copy all source group artifacts to new group
5. Add any missing artifacts to target collection
6. Commit all changes atomically

### Error Handling

All database errors are caught and converted to appropriate HTTP exceptions:
- **Uniqueness violation**: Returns 400 Bad Request
- **Missing records**: Returns 404 Not Found
- **Other DB errors**: Returns 500 Internal Server Error

### Logging

The operation is logged with:
- Source group name and ID
- Target collection ID
- New group ID and name
- Number of artifacts copied

Example log:
```
Copied group 'Frontend Development' (group-123) to collection 'another-collection-456'
as 'Frontend Development (Copy)' (new-group-789) with 5 artifacts
```

---

## OpenAPI Specification

The endpoint is fully documented in the OpenAPI spec:

```yaml
paths:
  /groups/{group_id}/copy:
    post:
      summary: Copy group to another collection
      description: >
        Copy a group with all its artifacts to another collection.
        The new group will have the same name with " (Copy)" suffix.
        If an artifact is not already in the target collection, it will be added.
        Duplicate artifacts (already in target collection) are silently skipped.
      operationId: copy_group_api_v1_groups__group_id__copy_post
      parameters:
        - name: group_id
          in: path
          required: true
          schema:
            type: string
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CopyGroupRequest'
      responses:
        '201':
          description: Group successfully copied
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/GroupResponse'
        '400':
          description: Bad request (duplicate name, etc.)
        '404':
          description: Source group or target collection not found
        '422':
          description: Validation error in request body
        '500':
          description: Internal server error
```

---

## Changelog

### Version 1.0.0 (2025-01-16)

- Initial endpoint documentation
- Complete request/response schema documentation
- Usage examples for multiple languages
- Error handling documentation
- Behavior specification

