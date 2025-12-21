# MCP Server Management Architecture

Technical architecture documentation for the MCP (Model Context Protocol) Server Management system in SkillMeat.

## System Overview

The MCP management system enables SkillMeat to manage Model Context Protocol servers throughout their entire lifecycle:

```
┌─────────────────────────────────────────────────────────┐
│                    SkillMeat Users                      │
│  (Local Dev, Teams, CI/CD, System Administrators)       │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬─────────────────┐
        │                     │                 │
        ▼                     ▼                 ▼
    ┌────────┐            ┌──────────┐      ┌──────────┐
    │   CLI  │            │  Web API │      │  Direct  │
    │        │            │          │      │   File   │
    └────┬───┘            └────┬─────┘      │   Ops    │
         │                     │             └────┬─────┘
         └──────────┬──────────┴───────────────────┘
                    │
                    ▼
         ┌──────────────────────────┐
         │   Collection Manager     │
         │  (Artifact + MCP Track)  │
         └──────┬────────┬──────────┘
                │        │
        ┌───────▼──┐   ┌─▼──────────┐
        │ Metadata │   │  Storage   │
        │  Models  │   │  & Config  │
        └────┬─────┘   └──┬────────┬─┘
             │            │        │
        ┌────▼─────────────▼┐  ┌──▼─────────┐
        │                   │  │ collection │
        │   MCP Management  │  │   .toml    │
        │   (3 Layers)      │  └────────────┘
        │                   │
        ├─ Metadata Layer  │
        │ ├─ Models       │
        │ └─ Validation   │
        │                 │
        ├─ Deployment    │
        │ ├─ Settings.json
        │ └─ Atomic ops  │
        │                 │
        ├─ Health Check   │
        │ ├─ Log parsing  │
        │ └─ Caching      │
        └────┬────────────┘
             │
             ▼
     ┌───────────────┐
     │  Claude       │
     │  Desktop      │
     │  Config File  │
     └───────────────┘
```

## Component Breakdown

### 1. Metadata Model Layer

**Module**: `skillmeat/core/mcp/metadata.py`

Defines data models for MCP server configuration and state:

#### MCPServerMetadata

```python
@dataclass
class MCPServerMetadata:
    """Represents an MCP server in a SkillMeat collection."""
    name: str                              # Unique identifier
    repo: str                              # GitHub source
    version: str = "latest"                # Version spec
    env_vars: Dict[str, str]              # Configuration vars
    description: Optional[str]             # Human description
    installed_at: Optional[str]           # Installation timestamp
    status: MCPServerStatus                # Current status
    resolved_sha: Optional[str]            # Git commit SHA
    resolved_version: Optional[str]        # Resolved tag/version
    last_updated: Optional[str]            # Update timestamp
```

#### MCPServerStatus

```python
class MCPServerStatus(str, Enum):
    INSTALLED = "installed"        # Deployed to Claude Desktop
    NOT_INSTALLED = "not_installed" # In collection, not deployed
    ERROR = "error"                 # Failed to deploy
    UPDATING = "updating"           # Update in progress
```

**Responsibilities**:
- Model validation (name format, repo URL)
- Type safety for server configurations
- Serialization/deserialization for storage
- Status tracking throughout lifecycle

**Key Features**:
- Security validation (no path traversal in names)
- URL parsing and validation
- Field validation in `__post_init__`
- Immutable status enumeration

### 2. Deployment Layer

**Module**: `skillmeat/core/mcp/deployment.py`

Manages deployment of MCP servers to Claude Desktop:

#### MCPDeploymentManager

```python
class MCPDeploymentManager:
    """Handles deployment to Claude Desktop settings.json."""

    def deploy(self, server: MCPServerMetadata, settings_path: Path) -> DeploymentResult
    def undeploy(self, server_name: str, settings_path: Path) -> bool
    def get_settings_path(self) -> Path  # Platform-specific path
    def _backup_settings(self, settings_path: Path) -> Path
    def _restore_backup(self, settings_path: Path, backup_path: Path) -> bool
```

**Platform Support**:

```python
# macOS
~/Library/Application Support/Claude/claude_desktop_config.json

# Linux
~/.config/Claude/claude_desktop_config.json

# Windows
%APPDATA%\Claude\claude_desktop_config.json
```

**Deployment Workflow**:

```
User requests deployment
        │
        ▼
    Backup current settings.json
        │
        ▼
    Clone repository from GitHub
        │
        ▼
    Parse package.json for entry point
        │
        ▼
    Build server configuration entry
        │
        ▼
    Merge into settings.json (idempotent)
        │
        ▼
    Atomic write to settings.json
        │
        ▼
    Update metadata (status = INSTALLED)
        │
        └─ Success: Return DeploymentResult
        └─ Error: Restore backup, return error
```

**Key Features**:
- Atomic updates (all-or-nothing)
- Automatic backup before changes
- Rollback capability on failure
- Idempotent (can deploy multiple times)
- Platform-specific path detection
- Environment variable injection

#### DeploymentResult

```python
@dataclass
class DeploymentResult:
    server_name: str
    success: bool
    settings_path: Path
    backup_path: Optional[Path] = None
    env_file_path: Optional[Path] = None
    error_message: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
```

### 3. Health Checking Layer

**Module**: `skillmeat/core/mcp/health.py`

Monitors deployed MCP servers:

#### MCPHealthChecker

```python
class MCPHealthChecker:
    """Checks health of deployed MCP servers."""

    def check_server_health(self, server_name: str) -> HealthCheckResult
    def check_all_servers(self) -> List[HealthCheckResult]
    def _parse_logs(self, server_name: str) -> LogEntry[]
    def get_cached_result(self, server_name: str) -> Optional[HealthCheckResult]
```

**Health Determination Logic**:

```
Check if server in settings.json
    │
    ├─ No → Status: NOT_DEPLOYED
    │
    └─ Yes, in settings.json
        │
        ├─ Parse Claude Desktop logs for server activity
        │   │
        │   ├─ Recent errors found → UNHEALTHY
        │   ├─ Recent warnings found → DEGRADED
        │   ├─ Recent success logs → HEALTHY
        │   └─ No logs in past hour → UNKNOWN
        │
        ├─ Count errors/warnings in recent period
        │
        └─ Cache result for 60 seconds
```

#### HealthStatus

```python
class HealthStatus(str, Enum):
    HEALTHY = "healthy"       # Running well
    DEGRADED = "degraded"     # Running with warnings
    UNHEALTHY = "unhealthy"   # Deployed but failing
    UNKNOWN = "unknown"        # Status cannot be determined
    NOT_DEPLOYED = "not_deployed"  # Not in settings.json
```

#### HealthCheckResult

```python
@dataclass
class HealthCheckResult:
    server_name: str
    status: HealthStatus
    deployed: bool
    last_seen: Optional[datetime] = None
    error_count: int = 0
    warning_count: int = 0
    recent_errors: List[str] = field(default_factory=list)
    recent_warnings: List[str] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.utcnow)
```

**Key Features**:
- Log-based health detection (no server-side probes)
- Configurable cache duration
- Error/warning aggregation
- Recent activity tracking
- Graceful handling of missing logs

### 4. API Layer

**Module**: `skillmeat/api/routers/mcp.py`

REST API endpoints for MCP management:

#### Endpoints

```
GET    /mcp                    # List all MCP servers
GET    /mcp/<name>            # Get server details
POST   /mcp                    # Create MCP server
PUT    /mcp/<name>            # Update MCP server
DELETE /mcp/<name>            # Remove MCP server

POST   /mcp/<name>/deploy      # Deploy server
POST   /mcp/<name>/undeploy    # Undeploy server
GET    /mcp/<name>/health      # Check health

POST   /mcp/backup             # Create backup
POST   /mcp/restore            # Restore from backup
GET    /mcp/logs/<name>        # Get server logs
```

#### Request/Response Schemas

**Create Server Request**:
```python
@dataclass
class MCPServerCreateRequest:
    name: str
    repo: str
    version: str = "latest"
    description: Optional[str] = None
    env_vars: Dict[str, str] = field(default_factory=dict)
```

**Deploy Request**:
```python
@dataclass
class DeploymentRequest:
    server_name: str
    dry_run: bool = False
```

**Health Response**:
```python
@dataclass
class HealthCheckResponse:
    server_name: str
    status: str  # from HealthStatus enum
    deployed: bool
    last_seen: Optional[str]  # ISO 8601
    error_count: int
    warning_count: int
```

## Data Flow

### Adding an MCP Server

```
User input (CLI/Web UI)
        │
        ▼
    Validate input
    └─ Name format check
    └─ Repository URL validation
    └─ Version format check
        │
        ▼
    Create MCPServerMetadata instance
        │
        ▼
    Add to collection.mcp_servers[]
        │
        ▼
    Persist to collection.toml
    [collection]
    mcp_servers = [
        {name = "filesystem", repo = "anthropics/mcp-filesystem", ...}
    ]
        │
        ▼
    Return to user
    Status: not_installed
```

### Deploying an MCP Server

```
User requests deployment
        │
        ▼
    Retrieve server metadata from collection
        │
        ▼
    MCPDeploymentManager.deploy()
    │
    ├─ Create backup of current settings.json
    │   Backup file: ~/.config/Claude/backup_YYYY-MM-DD_HH-MM.json
    │
    ├─ Clone GitHub repository
    │   └─ Use GitHub token if available
    │   └─ Resolve version tag to commit SHA
    │
    ├─ Parse package.json for entry point
    │   Example: {"scripts": {"start": "node dist/index.js"}}
    │
    ├─ Build settings entry:
    │   "filesystem": {
    │     "command": "node",
    │     "args": ["/path/to/server/dist/index.js"],
    │     "env": {"ROOT_PATH": "/home/user/projects"}
    │   }
    │
    ├─ Read current settings.json
    │
    ├─ Merge new entry (idempotent update)
    │   └─ If server exists, update its entry
    │   └─ If new, append to mcpServers object
    │
    ├─ Atomic write:
    │   1. Write to temp file
    │   2. Verify JSON validity
    │   3. Move temp → settings.json (atomic on POSIX)
    │
    └─ Update metadata
        server.status = INSTALLED
        server.installed_at = now()
        Persist to collection.toml
            │
            ▼
        Return DeploymentResult
        success = true
```

### Health Check Flow

```
User requests health check
        │
        ▼
    Check cache (valid for 60s)
    ├─ If cached result exists → Return cached
    └─ If expired/missing → Continue
        │
        ▼
    Check if server in settings.json
    ├─ No → Return NOT_DEPLOYED
    └─ Yes → Continue
        │
        ▼
    Parse Claude Desktop logs
    │
    ├─ Locate log files (platform-specific)
    │   macOS: ~/Library/Logs/Claude/
    │   Linux: ~/.local/share/Claude/logs/
    │   Windows: %APPDATA%\Claude\logs\
    │
    ├─ Search for server name in recent logs
    │   Pattern: "MCP server 'filesystem'" or similar
    │
    ├─ Categorize log entries by level:
    │   ERROR, WARN, INFO, DEBUG
    │
    ├─ Determine status:
    │   ├─ If recent errors → UNHEALTHY
    │   ├─ If recent warnings → DEGRADED
    │   ├─ If recent success → HEALTHY
    │   └─ If no logs → UNKNOWN
    │
    └─ Build HealthCheckResult
        ├─ server_name
        ├─ status
        ├─ deployed
        ├─ last_seen (from logs)
        ├─ error_count
        ├─ warning_count
        ├─ recent_errors (last 5)
        ├─ recent_warnings (last 5)
        └─ checked_at
            │
            ▼
        Cache result for 60 seconds
        Return to user
```

## State Management

### Collection Storage

MCP servers stored in collection manifest:

```toml
# collection.toml
[collection]
name = "default"
version = "1.0.0"

[[mcp_servers]]
name = "filesystem"
repo = "anthropics/mcp-filesystem"
version = "v1.0.0"
status = "installed"
env_vars = { ROOT_PATH = "/home/user" }
installed_at = "2024-01-15T14:30:00Z"
resolved_sha = "abc123def456"
resolved_version = "v1.0.0"
last_updated = "2024-01-15T14:30:00Z"
```

### Claude Desktop Settings

MCP servers deployed to settings.json:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "node",
      "args": [
        "/path/to/server/dist/index.js"
      ],
      "env": {
        "ROOT_PATH": "/home/user/projects"
      }
    },
    "github": {
      "command": "node",
      "args": [
        "/path/to/server/dist/index.js"
      ],
      "env": {
        "GITHUB_TOKEN": "ghp_xxx",
        "GITHUB_USER": "username"
      }
    }
  }
}
```

### Status Lifecycle

```
NOT_INSTALLED  (in collection, not deployed)
     │
     ├─ User clicks deploy
     └─ MCPDeploymentManager.deploy()
             │
             ├─ Success → INSTALLED ✓
             │
             └─ Error → ERROR
                    │
                    ├─ User fixes issue
                    └─ Retry → INSTALLED ✓

INSTALLED (deployed to Claude)
     │
     ├─ Health check: HEALTHY ✓
     │
     ├─ Health check: DEGRADED ⚠
     │    (has warnings)
     │
     ├─ Health check: UNHEALTHY ✗
     │    (has errors)
     │
     ├─ User requests undeploy
     └─ MCPDeploymentManager.undeploy()
         → NOT_INSTALLED
```

## Error Handling

### Deployment Error Handling

```python
def deploy(self, server: MCPServerMetadata) -> DeploymentResult:
    try:
        # Create backup first
        backup = self._backup_settings(settings_path)

        # Clone and configure
        repo = self._clone_repo(server.repo, server.version)
        entry = self._build_entry(repo, server)

        # Atomic write
        settings = self._read_settings(settings_path)
        settings['mcpServers'][server.name] = entry
        self._write_settings_atomically(settings_path, settings)

        # Success
        return DeploymentResult(success=True, ...)

    except Exception as e:
        # Rollback on any error
        self._restore_backup(settings_path, backup)
        return DeploymentResult(success=False, error_message=str(e))
```

### Validation Error Handling

```python
def __post_init__(self):
    """Validate metadata."""
    # Name validation
    if not self.name:
        raise ValueError("name cannot be empty")

    if not re.match(r"^[a-zA-Z0-9_-]+$", self.name):
        raise ValueError(f"Invalid server name: {self.name}")

    # URL validation
    if not self._is_valid_github_url(self.repo):
        raise ValueError(f"Invalid repository: {self.repo}")
```

## Extension Points

### Adding New MCP Server Sources

Currently supports GitHub. To add other sources:

```python
# skillmeat/sources/mcp_sources.py

class MCPServerSource(ABC):
    """Base class for MCP server sources."""

    @abstractmethod
    def resolve_version(self, spec: str) -> Tuple[str, str]:
        """Return (resolved_sha, resolved_version)."""
        pass

    @abstractmethod
    def clone(self, spec: str, version: str) -> Path:
        """Clone and return local path."""
        pass

class GitHubMCPSource(MCPServerSource):
    """GitHub implementation."""
    pass

class LocalMCPSource(MCPServerSource):
    """Local file system implementation."""
    pass
```

### Custom Health Checks

```python
# Extend MCPHealthChecker for custom logic

class CustomHealthChecker(MCPHealthChecker):
    def check_server_health(self, server_name: str) -> HealthCheckResult:
        result = super().check_server_health(server_name)

        # Add custom checks
        if server_name == "database":
            # Ping database to verify connectivity
            if not self._check_db_connection():
                result.status = HealthStatus.UNHEALTHY

        return result
```

## Performance Considerations

### Health Check Caching

- Default cache duration: 60 seconds
- Prevents excessive log parsing
- Cache invalidated on deployment
- Configurable via settings

### Deployment Optimization

- Parallel server deployment (if needed):
  ```python
  from concurrent.futures import ThreadPoolExecutor

  with ThreadPoolExecutor(max_workers=3) as executor:
      futures = [executor.submit(deploy, server) for server in servers]
  ```

### Log Parsing Efficiency

- Only parse logs from last 1 hour
- Use pattern matching for quick filtering
- Cache parsing results per server
- Limit to last 100 log entries per server

## Security Considerations

### Secret Management

1. **Environment Variables**: Stored in collection.toml
   - Treat file as sensitive
   - Consider disk encryption
   - Rotate secrets regularly

2. **GitHub Tokens**:
   - Stored in config (~/.skillman/config.toml)
   - Use GitHub's personal access tokens
   - Limit token scope (repo only)
   - Rotate regularly

3. **Deployment Safety**:
   - Always create backup before deployment
   - Atomic writes prevent partial states
   - Rollback on error
   - Signed commits tracking (future)

### Input Validation

```python
# Server name: [a-zA-Z0-9_-]
# Repository: owner/repo format
# Version: semantic version or git ref
# Environment variables: no special shell chars
```

## Platform Abstraction

The system abstracts platform differences:

```python
def get_settings_path(self) -> Path:
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library/Application Support/Claude"
    elif system == "Windows":
        return Path(os.environ["APPDATA"]) / "Claude"
    elif system == "Linux":
        return Path.home() / ".config/Claude"
    else:
        raise RuntimeError(f"Unsupported: {system}")
```

Same for log locations and configuration paths.

## Testing Strategy

### Unit Tests (80% coverage)

- MCPServerMetadata validation
- Deployment logic (mocked GitHub)
- Health check result building
- API endpoint responses

### Integration Tests

- End-to-end deployment workflow
- Multi-server management
- Error recovery/rollback
- Health check accuracy

### Manual Testing

- Actual Claude Desktop deployment
- Real server startup and health
- Cross-platform verification

## Future Enhancements

1. **MCP Server Registry**: Central registry of verified servers
2. **Version Resolution**: Better semantic versioning support
3. **Dependency Management**: Handle server dependencies
4. **Resource Limits**: CPU/memory constraints per server
5. **Server Scheduling**: Start/stop on demand
6. **Metrics Collection**: Performance and usage analytics
7. **Update Strategy**: Auto-update with version pinning options
8. **Team Sharing**: Share server configs across teams
