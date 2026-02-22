# Marketplace Import Path Construction Investigation

## Error Context
The error shows: "plugins/frontend-tools" path being requested but returning 404.

## Key Findings

### 1. **Path Construction Flow** (Import Coordinator)

**File**: `skillmeat/core/marketplace/import_coordinator.py`

The ImportCoordinator constructs artifact paths through:

1. **GitHub Download Flow** (`_download_artifact`):
   - Parses GitHub URLs: `https://github.com/{owner}/{repo}/tree/{ref}/{path}`
   - Example: `https://github.com/user/repo/tree/main/plugins/frontend-tools`
   - Extracts: owner=`user`, repo=`repo`, ref=`main`, path=`plugins/frontend-tools`
   - **This path is then passed directly to GitHub API for download**

2. **GitHub API Call** (`_download_directory_recursive`):
   ```python
   api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{remote_path}"
   # With params: {"ref": ref}
   ```
   - Line 586: Constructs API endpoint using the extracted `remote_path`
   - **The error occurs when GitHub API returns 404 for this path**

### 2. **Where "plugins" Path Comes From**

**File**: `skillmeat/api/routers/marketplace_sources.py` (line 1278)

The comment shows the expected path format:
```python
# e.g., "plugins/web-scripting/agents/ruby-pro.md", "commands/doc-generate.md"
for artifact in artifacts:
    artifact_path = artifact.path.rstrip("/")
```

The "plugins" segment comes from:

1. **GitHub Scanning** → **Heuristic Detection** → **File Tree Analysis**:

   **File**: `skillmeat/core/marketplace/github_scanner.py`
   - Line 467: `tree = self._client.get_repo_tree(owner_repo, ref=ref, recursive=True)`
   - Line 284: `file_paths = self._extract_file_paths(tree, root_hint)`
   - Returns: List of ALL file paths in the repository (extracted from GitHub tree API)

   **File**: `skillmeat/core/marketplace/heuristic_detector.py`
   - Line 2524: `matches = detector.analyze_paths(file_tree, base_url=repo_url, root_hint=root_hint)`
   - Analyzes each path to detect artifacts
   - Line 2458: `path=match.path` - Sets the detected artifact's path

   **File**: `skillmeat/api/routers/marketplace_catalog.py`
   - The path is stored in MarketplaceCatalogEntry table
   - Retrieved and displayed in the UI

### 3. **Path Is From Repository's Actual Directory Structure**

The "plugins" path segment comes from the **repository's actual file/directory structure**.

When GitHub scanner runs:
1. Fetches complete repository tree via GitHub API: `GET /repos/{owner}/{repo}/git/trees/{sha}?recursive=1`
2. Returns ALL paths: `["plugins/", "plugins/frontend-tools/", "plugins/frontend-tools/README.md", ...]`
3. Heuristic detector receives these paths as-is
4. Returns artifacts with their original repository paths

**Example GitHub tree structure** (what GitHub API returns):
```
plugins/
plugins/frontend-tools/
plugins/frontend-tools/README.md
plugins/frontend-tools/index.ts
plugins/web-scripting/
plugins/web-scripting/agents/ruby-pro.md
commands/
commands/doc-generate.md
```

### 4. **How Artifact Paths Map to GitHub URLs**

**Path-to-URL Mapping** (marketplace_sources.py, line 2453):
```python
upstream_url = f"{base_url.rstrip('/')}/tree/{ref}/{match.path}"
# Result: https://github.com/{owner}/{repo}/tree/{ref}/plugins/frontend-tools
```

**When downloading**, ImportCoordinator extracts and uses this path:
```python
# Line 474: owner, repo, ref, path = _parse_github_url(entry.upstream_url)
# Line 586: api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{remote_path}"
# Result: https://api.github.com/repos/{owner}/{repo}/contents/plugins/frontend-tools
```

### 5. **Why 404 Occurs**

The 404 error happens when:

1. **Heuristic detector returns**: `path="plugins/frontend-tools"`
2. **This path is stored in** MarketplaceCatalogEntry
3. **When downloading**, code constructs: `https://api.github.com/repos/{owner}/{repo}/contents/plugins/frontend-tools`
4. **GitHub API returns 404 if**:
   - The path doesn't exist in the repository
   - OR the directory was a composite/plugin directory with no manifest file at root
   - OR the directory structure changed between scan and download

### 6. **Mapping Between Artifact Types and Directory Names**

**File**: `skillmeat/core/marketplace/heuristic_detector.py` (lines 117-159)

**CONTAINER_TYPE_MAPPING**:
```python
{
    "commands": ArtifactType.COMMAND,
    "agents": ArtifactType.AGENT,
    "skills": ArtifactType.SKILL,
    "hooks": ArtifactType.HOOK,
    "mcp": ArtifactType.MCP,
    "mcp-servers": ArtifactType.MCP,
    "servers": ArtifactType.MCP,
}
```

**Detection Configuration** (DetectionConfig class, lines 167-175):
```python
dir_patterns: Dict[ArtifactType, Set[str]] = {
    ArtifactType.SKILL: {"skills", "skill", "claude-skills"},
    ArtifactType.COMMAND: {"commands", "command", "claude-commands"},
    ArtifactType.AGENT: {"agents", "agent", "claude-agents"},
    ArtifactType.MCP: {"mcp", "mcp-servers", "servers"},
    ArtifactType.HOOK: {"hooks", "hook", "claude-hooks"},
}
```

**Manifest Files by Type** (lines 178-186):
```python
manifest_files: Dict[ArtifactType, Set[str]] = {
    ArtifactType.SKILL: {"SKILL.md", "skill.md"},
    ArtifactType.COMMAND: {"COMMAND.md", "command.md"},
    ArtifactType.AGENT: {"AGENT.md", "agent.md"},
    ArtifactType.MCP: {"MCP.md", "mcp.md", "server.json"},
    ArtifactType.HOOK: {"HOOK.md", "hook.md", "hooks.json"},
}
```

**Note**: "plugins" is NOT a standard container directory. It's detected as a **composite/plugin directory** (multi-artifact package).

### 7. **Plugin/Composite Directory Detection**

**File**: `skillmeat/core/marketplace/heuristic_detector.py` (line 1128)

```python
# Detect composite/plugin directories FIRST
plugin_matches, plugin_dirs = self._detect_plugin_directories(
    dir_to_files, root_hint
)
```

A directory is detected as a plugin if:
- Contains subdirectories that are themselves artifacts (skills, commands, agents, etc.)
- Does NOT have its own manifest file
- Acts as a container/grouping directory

The "plugins" directory is likely being detected as a composite/plugin directory containing multiple artifact subdirectories.

## Directory Structure Sources

**How directory structures are defined**:

1. **Repository's Actual Structure**: Primary source - GitHub API returns what's actually in the repo
2. **Manual Mappings**: Can override detection via `manual_mappings` parameter
3. **Root Hint**: Can focus scanning on a subdirectory
4. **Single Artifact Mode**: Can treat entire repo as single artifact

**Example from marketplace_sources.py** (lines 1543-1543):
```python
artifact_path = source.root_hint if source.root_hint else ""
# Source.root_hint allows specifying where artifacts are located
```

## Import Flow Summary

1. **Scanner** → Gets GitHub repo tree with ALL paths
2. **Heuristic Detector** → Analyzes paths, detects artifacts with their original paths
3. **Catalog** → Stores detected artifacts with their paths
4. **Import Request** → User selects artifact to import
5. **Coordinator** → Extracts path from URL, constructs GitHub API call
6. **GitHub API** → Returns 404 if path doesn't exist in that form

## Potential Issues with "plugins/frontend-tools" 404

1. **Path mismatch**: The stored path "plugins/frontend-tools" might not be a downloadable directory
2. **Composite directory**: If "plugins/frontend-tools" is a composite directory detected but has no root manifest, it won't download
3. **Repository structure change**: Path existed when scanned but changed before download
4. **Member artifacts only**: The directory might contain member artifacts (e.g., `plugins/frontend-tools/agents/ruby-pro.md`) but not have a `plugins/frontend-tools/SKILL.md` or similar manifest
