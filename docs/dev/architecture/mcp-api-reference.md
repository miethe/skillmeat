# MCP Server Management API Reference

Complete OpenAPI reference for MCP server management endpoints in SkillMeat.

## Base Information

- **API Version**: 1.0.0
- **Base URL**: `http://localhost:8000/api/v1`
- **Authentication**: API Key (header: `X-API-Key`)
- **Rate Limit**: 100 requests/minute per API key
- **Content Type**: `application/json`

## Authentication

### API Key Authentication

All endpoints require API key authentication:

```bash
# Generate API token
skillmeat token create

# Use in requests
curl -H "X-API-Key: your_api_key_here" \
  http://localhost:8000/api/v1/mcp
```

### Response Headers

Every response includes rate limit information:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 99
X-RateLimit-Reset: 1705339200
```

## Endpoints

### List MCP Servers

**Endpoint**: `GET /mcp`

**Description**: List all MCP servers in the active collection.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `status` | string | Filter by status (installed, not_installed, error) | - |
| `limit` | integer | Maximum results to return | 100 |
| `offset` | integer | Pagination offset | 0 |

**Request**:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/mcp?status=installed' \
  -H 'X-API-Key: your_api_key'
```

**Response (200 OK)**:

```json
{
  "servers": [
    {
      "name": "filesystem",
      "repo": "anthropics/mcp-filesystem",
      "version": "v1.0.0",
      "description": "File system access server",
      "status": "installed",
      "deployed": true,
      "env_vars": {
        "ROOT_PATH": "/home/user/projects"
      },
      "installed_at": "2024-01-15T14:30:00Z",
      "last_updated": "2024-01-15T14:30:00Z",
      "resolved_sha": "abc123def456",
      "resolved_version": "v1.0.0"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

**Error Responses**:

```json
{
  "error": {
    "code": "INVALID_FILTER",
    "message": "Invalid status filter"
  }
}
```

---

### Get MCP Server Details

**Endpoint**: `GET /mcp/{server_name}`

**Description**: Get detailed information about a specific MCP server.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `server_name` | string | Name of the MCP server |

**Request**:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/mcp/filesystem' \
  -H 'X-API-Key: your_api_key'
```

**Response (200 OK)**:

```json
{
  "name": "filesystem",
  "repo": "anthropics/mcp-filesystem",
  "version": "v1.0.0",
  "description": "File system access server with sandboxing",
  "status": "installed",
  "deployed": true,
  "env_vars": {
    "ROOT_PATH": "/home/user/projects"
  },
  "installed_at": "2024-01-15T14:30:00Z",
  "last_updated": "2024-01-15T14:30:00Z",
  "resolved_sha": "abc123def456",
  "resolved_version": "v1.0.0",
  "deployed_config": {
    "command": "node",
    "args": ["/path/to/server/dist/index.js"],
    "env": {
      "ROOT_PATH": "/home/user/projects"
    }
  }
}
```

**Error Responses**:

```json
{
  "error": {
    "code": "SERVER_NOT_FOUND",
    "message": "Server 'filesystem' not found"
  }
}
```

---

### Create MCP Server

**Endpoint**: `POST /mcp`

**Description**: Add a new MCP server to the collection.

**Authentication**: Required

**Request Body**:

```json
{
  "name": "github",
  "repo": "anthropics/mcp-github",
  "version": "latest",
  "description": "GitHub repository operations",
  "env_vars": {
    "GITHUB_TOKEN": "ghp_xxxxxxxxxxxx",
    "GITHUB_USER": "username"
  }
}
```

**Request**:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/mcp' \
  -H 'X-API-Key: your_api_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "github",
    "repo": "anthropics/mcp-github",
    "version": "latest",
    "env_vars": {
      "GITHUB_TOKEN": "ghp_xxx"
    }
  }'
```

**Response (201 Created)**:

```json
{
  "name": "github",
  "repo": "anthropics/mcp-github",
  "version": "latest",
  "status": "not_installed",
  "deployed": false,
  "env_vars": {
    "GITHUB_TOKEN": "****"  # Masked in response
  }
}
```

**Request Schema**:

```typescript
interface MCPServerCreateRequest {
  name: string;                      // [a-zA-Z0-9_-]
  repo: string;                      // owner/repo format
  version?: string;                  // default: "latest"
  description?: string;
  env_vars?: Record<string, string>;
}
```

**Error Responses**:

```json
{
  "error": {
    "code": "INVALID_NAME",
    "message": "Server name contains invalid characters"
  }
}
```

```json
{
  "error": {
    "code": "DUPLICATE_SERVER",
    "message": "Server 'github' already exists"
  }
}
```

---

### Update MCP Server

**Endpoint**: `PUT /mcp/{server_name}`

**Description**: Update an existing MCP server configuration.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `server_name` | string | Name of the MCP server |

**Request Body**:

```json
{
  "version": "v2.0.0",
  "description": "Updated description",
  "env_vars": {
    "GITHUB_TOKEN": "ghp_new_token",
    "GITHUB_USER": "newuser"
  }
}
```

**Request**:

```bash
curl -X PUT \
  'http://localhost:8000/api/v1/mcp/github' \
  -H 'X-API-Key: your_api_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "version": "v2.0.0",
    "env_vars": {
      "GITHUB_TOKEN": "ghp_new_token"
    }
  }'
```

**Response (200 OK)**:

```json
{
  "name": "github",
  "repo": "anthropics/mcp-github",
  "version": "v2.0.0",
  "status": "installed",
  "deployed": true,
  "env_vars": {
    "GITHUB_TOKEN": "****"
  }
}
```

**Request Schema**:

```typescript
interface MCPServerUpdateRequest {
  version?: string;
  description?: string;
  env_vars?: Record<string, string>;
}
```

---

### Delete MCP Server

**Endpoint**: `DELETE /mcp/{server_name}`

**Description**: Remove an MCP server from the collection.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `server_name` | string | Name of the MCP server |

**Query Parameters**:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `undeploy_first` | boolean | Undeploy from Claude if deployed | true |

**Request**:

```bash
curl -X DELETE \
  'http://localhost:8000/api/v1/mcp/github?undeploy_first=true' \
  -H 'X-API-Key: your_api_key'
```

**Response (204 No Content)**:

No response body on successful deletion.

**Error Responses**:

```json
{
  "error": {
    "code": "SERVER_NOT_FOUND",
    "message": "Server 'github' not found"
  }
}
```

---

### Deploy MCP Server

**Endpoint**: `POST /mcp/{server_name}/deploy`

**Description**: Deploy an MCP server to Claude Desktop.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `server_name` | string | Name of the MCP server |

**Request Body**:

```json
{
  "dry_run": false
}
```

**Request**:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/mcp/filesystem/deploy' \
  -H 'X-API-Key: your_api_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "dry_run": false
  }'
```

**Response (200 OK)**:

```json
{
  "success": true,
  "server_name": "filesystem",
  "settings_path": "/home/user/.config/Claude/claude_desktop_config.json",
  "backup_path": "/home/user/.config/Claude/backup_2024-01-15_14-30.json",
  "command": "node",
  "args": [
    "/path/to/server/dist/index.js"
  ]
}
```

**Dry Run Response (200 OK)**:

```json
{
  "success": true,
  "dry_run": true,
  "changes": {
    "add_servers": ["filesystem"],
    "update_servers": [],
    "remove_servers": [],
    "preview": {
      "filesystem": {
        "command": "node",
        "args": ["/path/to/server/dist/index.js"],
        "env": {
          "ROOT_PATH": "/home/user/projects"
        }
      }
    }
  }
}
```

**Request Schema**:

```typescript
interface DeploymentRequest {
  dry_run?: boolean;  // Preview changes without applying
}
```

**Error Responses**:

```json
{
  "error": {
    "code": "DEPLOYMENT_FAILED",
    "message": "Failed to clone repository: authentication failed"
  }
}
```

---

### Undeploy MCP Server

**Endpoint**: `POST /mcp/{server_name}/undeploy`

**Description**: Remove an MCP server from Claude Desktop.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `server_name` | string | Name of the MCP server |

**Request**:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/mcp/filesystem/undeploy' \
  -H 'X-API-Key: your_api_key'
```

**Response (200 OK)**:

```json
{
  "success": true,
  "server_name": "filesystem",
  "message": "Server undeployed from Claude Desktop"
}
```

---

### Check MCP Server Health

**Endpoint**: `GET /mcp/{server_name}/health`

**Description**: Check the health status of a deployed MCP server.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `server_name` | string | Name of the MCP server |

**Query Parameters**:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `force` | boolean | Bypass cache and do fresh check | false |

**Request**:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/mcp/filesystem/health?force=false' \
  -H 'X-API-Key: your_api_key'
```

**Response (200 OK)**:

```json
{
  "server_name": "filesystem",
  "status": "healthy",
  "deployed": true,
  "last_seen": "2024-01-15T14:35:22Z",
  "error_count": 0,
  "warning_count": 0,
  "recent_errors": [],
  "recent_warnings": [],
  "checked_at": "2024-01-15T14:35:25Z"
}
```

**Health Status Values**:

| Status | Meaning |
|--------|---------|
| `healthy` | Server running normally |
| `degraded` | Running with warnings |
| `unhealthy` | Deployed but failing |
| `unknown` | Status cannot be determined |
| `not_deployed` | Not in settings.json |

---

### Get All Health Status

**Endpoint**: `GET /mcp/health`

**Description**: Check health of all MCP servers.

**Authentication**: Required

**Query Parameters**:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `include_healthy` | boolean | Include healthy servers in response | true |

**Request**:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/mcp/health?include_healthy=true' \
  -H 'X-API-Key: your_api_key'
```

**Response (200 OK)**:

```json
{
  "checks": [
    {
      "server_name": "filesystem",
      "status": "healthy",
      "deployed": true,
      "last_seen": "2024-01-15T14:35:22Z",
      "error_count": 0,
      "warning_count": 0
    },
    {
      "server_name": "github",
      "status": "unhealthy",
      "deployed": true,
      "last_seen": "2024-01-15T14:20:15Z",
      "error_count": 3,
      "warning_count": 0,
      "recent_errors": [
        "Failed to authenticate with GitHub API",
        "Connection timeout",
        "Invalid token"
      ]
    }
  ],
  "summary": {
    "total": 2,
    "healthy": 1,
    "degraded": 0,
    "unhealthy": 1,
    "unknown": 0,
    "not_deployed": 0
  }
}
```

---

### Create Backup

**Endpoint**: `POST /mcp/backup`

**Description**: Create a backup of Claude Desktop settings.

**Authentication**: Required

**Request**:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/mcp/backup' \
  -H 'X-API-Key: your_api_key'
```

**Response (201 Created)**:

```json
{
  "success": true,
  "backup_path": "/home/user/.config/Claude/backup_2024-01-15_14-35.json",
  "timestamp": "2024-01-15T14:35:30Z",
  "servers_count": 2
}
```

---

### Restore Backup

**Endpoint**: `POST /mcp/restore`

**Description**: Restore Claude Desktop settings from a backup.

**Authentication**: Required

**Request Body**:

```json
{
  "backup_path": "/home/user/.config/Claude/backup_2024-01-15_14-35.json"
}
```

**Request**:

```bash
curl -X POST \
  'http://localhost:8000/api/v1/mcp/restore' \
  -H 'X-API-Key: your_api_key' \
  -H 'Content-Type: application/json' \
  -d '{
    "backup_path": "/home/user/.config/Claude/backup_2024-01-15_14-35.json"
  }'
```

**Response (200 OK)**:

```json
{
  "success": true,
  "message": "Restored from backup",
  "servers_count": 2
}
```

**Request Schema**:

```typescript
interface RestoreRequest {
  backup_path: string;  // Path to backup file
}
```

---

### Get Server Logs

**Endpoint**: `GET /mcp/{server_name}/logs`

**Description**: Get logs for a specific MCP server.

**Authentication**: Required

**Path Parameters**:

| Parameter | Type | Description |
|-----------|------|-------------|
| `server_name` | string | Name of the MCP server |

**Query Parameters**:

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `tail` | integer | Number of lines to return | 50 |
| `since` | string | ISO 8601 timestamp | Last 1 hour |
| `level` | string | Log level (ERROR, WARN, INFO, DEBUG) | - |

**Request**:

```bash
curl -X GET \
  'http://localhost:8000/api/v1/mcp/filesystem/logs?tail=100&level=ERROR' \
  -H 'X-API-Key: your_api_key'
```

**Response (200 OK)**:

```json
{
  "server_name": "filesystem",
  "logs": [
    {
      "timestamp": "2024-01-15T14:30:00Z",
      "level": "INFO",
      "message": "MCP server 'filesystem' started",
      "source": "claude_desktop"
    },
    {
      "timestamp": "2024-01-15T14:32:15Z",
      "level": "ERROR",
      "message": "Failed to access path: permission denied",
      "source": "mcp_server"
    }
  ],
  "total_lines": 150,
  "returned_lines": 2
}
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "field": "field_name",
      "constraint": "constraint_details"
    },
    "request_id": "req_abc123def456"
  },
  "status_code": 400
}
```

### Common Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `INVALID_NAME` | 400 | Server name format invalid |
| `INVALID_REPO` | 400 | Repository URL format invalid |
| `DUPLICATE_SERVER` | 409 | Server with this name already exists |
| `SERVER_NOT_FOUND` | 404 | Requested server doesn't exist |
| `DEPLOYMENT_FAILED` | 500 | Deployment operation failed |
| `CLONE_FAILED` | 500 | Failed to clone from GitHub |
| `AUTH_FAILED` | 401 | GitHub authentication failed |
| `SETTINGS_INVALID` | 500 | Claude settings.json is corrupted |
| `UNAUTHORIZED` | 401 | API key is missing or invalid |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |

---

## Examples

### Complete Workflow: Add and Deploy Server

```bash
#!/bin/bash
API_KEY="your_api_key"
BASE_URL="http://localhost:8000/api/v1"

# 1. Create server
echo "Creating MCP server..."
SERVER=$(curl -s -X POST "$BASE_URL/mcp" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "filesystem",
    "repo": "anthropics/mcp-filesystem",
    "version": "latest",
    "env_vars": {"ROOT_PATH": "/home/user"}
  }')

echo "$SERVER" | jq .

# 2. Dry run deployment
echo "Preview deployment..."
PREVIEW=$(curl -s -X POST "$BASE_URL/mcp/filesystem/deploy" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}')

echo "$PREVIEW" | jq '.changes'

# 3. Real deployment
echo "Deploying..."
DEPLOY=$(curl -s -X POST "$BASE_URL/mcp/filesystem/deploy" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"dry_run": false}')

echo "$DEPLOY" | jq .

# 4. Check health
echo "Checking health..."
sleep 5
HEALTH=$(curl -s -X GET "$BASE_URL/mcp/filesystem/health" \
  -H "X-API-Key: $API_KEY")

echo "$HEALTH" | jq .
```

### Error Handling Example

```bash
#!/bin/bash
API_KEY="your_api_key"
BASE_URL="http://localhost:8000/api/v1"

# Try to deploy with error handling
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/mcp/invalid/deploy" \
  -H "X-API-Key: $API_KEY")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" -ne 200 ]; then
  ERROR_CODE=$(echo "$BODY" | jq -r '.error.code')
  ERROR_MSG=$(echo "$BODY" | jq -r '.error.message')
  echo "Error ($ERROR_CODE): $ERROR_MSG"
  exit 1
fi

echo "Success!"
echo "$BODY" | jq .
```

---

## Rate Limiting

All endpoints are rate-limited to 100 requests per minute per API key.

When approaching the limit, the response will include:

```
X-RateLimit-Remaining: 10
```

When limit is exceeded (HTTP 429):

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Reset at 2024-01-15T14:40:00Z",
    "retry_after": 300
  }
}
```

---

## Performance Notes

- Average response time: 50-200ms
- Deployment time: 5-30 seconds (depends on repository size)
- Health check time: 100-500ms
- Maximum request payload: 1MB
- Connections: Keep-alive recommended
