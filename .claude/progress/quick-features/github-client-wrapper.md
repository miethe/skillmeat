---
type: quick-feature-plan
feature_slug: github-client-wrapper
parent_feature: github-pat-settings
status: completed
completed_at: 2026-01-17 21:30:00+00:00
created: 2026-01-17 20:00:00+00:00
estimated_scope: large
schema_version: 2
doc_type: quick_feature
---

# GitHub Client Wrapper

## Scope

Create a centralized GitHub API client wrapper using PyGithub that:
1. Handles all GitHub API calls for the entire app
2. Transparently uses PAT if available, unauthenticated otherwise
3. Token priority: ConfigManager → SKILLMEAT_GITHUB_TOKEN → GITHUB_TOKEN
4. Provides clean interface hiding auth complexity from callers
5. Integrates Settings page with Config file (show config value)

## Current State Analysis

### Files Making GitHub API Calls (to refactor)

| File | Lines | API Calls | Token Handling |
|------|-------|-----------|----------------|
| `skillmeat/sources/github.py` | 468 | 4 endpoints | GITHUB_TOKEN env only |
| `skillmeat/core/github_metadata.py` | 518 | 2 endpoints | SKILLMEAT/GITHUB env |
| `skillmeat/core/marketplace/github_scanner.py` | 982 | 4 endpoints | SKILLMEAT/GITHUB env |
| `skillmeat/core/scoring/github_stars_importer.py` | 546 | 1 endpoint | Param only (async) |
| `skillmeat/api/routers/settings.py` | 300+ | 1 endpoint | Direct requests |

### Token Storage Locations
- Config file: `~/.skillmeat/config.toml` at `settings.github-token`
- API Settings: `APISettings.github_token` (SKILLMEAT_GITHUB_TOKEN env)
- Multiple env vars: GITHUB_TOKEN, SKILLMEAT_GITHUB_TOKEN

## Implementation Plan

### Phase 1: Create Centralized Wrapper

**New File**: `skillmeat/core/github_client.py`

```python
# Core wrapper using PyGithub
class GitHubClientWrapper:
    """Centralized GitHub API client.

    Token priority:
    1. Explicit token parameter
    2. ConfigManager (settings.github-token)
    3. SKILLMEAT_GITHUB_TOKEN env var
    4. GITHUB_TOKEN env var
    5. Unauthenticated (60 req/hr)
    """

    def __init__(self, token: Optional[str] = None):
        self._token = self._resolve_token(token)
        self._client = self._create_client()

    # Public API methods:
    # - get_repo(owner_repo: str) -> Repository
    # - get_repo_metadata(owner_repo: str) -> RepoMetadata
    # - get_file_content(owner_repo: str, path: str, ref: str) -> bytes
    # - get_repo_tree(owner_repo: str, ref: str) -> List[TreeEntry]
    # - resolve_version(owner_repo: str, version: str) -> str (SHA)
    # - validate_token() -> TokenValidation
    # - get_rate_limit() -> RateLimitInfo
```

### Phase 2: Refactor Existing Code

1. **settings.py router**: Use wrapper for token validation
2. **sources/github.py**: Replace manual HTTP with wrapper calls
3. **github_metadata.py**: Replace manual HTTP with wrapper calls
4. **github_scanner.py**: Replace manual HTTP with wrapper calls
5. **github_stars_importer.py**: Add async wrapper or keep httpx

### Phase 3: Settings/Config Integration

- GET `/settings/github-token/status` should check ConfigManager first
- Settings page shows config value if set (password-style masked)
- Frontend loads initial state from combined config + API settings

## Affected Files

### New Files
- `skillmeat/core/github_client.py` - Centralized wrapper

### Modified Files
- `skillmeat/sources/github.py` - Use wrapper
- `skillmeat/core/github_metadata.py` - Use wrapper
- `skillmeat/core/marketplace/github_scanner.py` - Use wrapper
- `skillmeat/api/routers/settings.py` - Use wrapper for validation
- `skillmeat/web/components/settings/github-settings.tsx` - Show config value

## Implementation Steps

1. [x] Add PyGithub dependency to pyproject.toml
2. [x] Create `skillmeat/core/github_client.py` with GitHubClientWrapper
3. [x] Add tests for GitHubClientWrapper
4. [x] Refactor `skillmeat/api/routers/settings.py` to use wrapper
5. [x] Refactor `skillmeat/sources/github.py` to use wrapper
6. [x] Refactor `skillmeat/core/github_metadata.py` to use wrapper
7. [x] Refactor `skillmeat/core/marketplace/github_scanner.py` to use wrapper
8. [x] Update Settings page to show config file token if set
9. [x] Run tests, typecheck, build
10. [ ] Update documentation

## Testing

- Unit tests for GitHubClientWrapper token resolution
- Integration test for PyGithub operations (mocked)
- E2E test for settings page config integration
- Verify existing tests still pass after refactor

## Dependencies

- PyGithub>=2.8.0 (adds retry support)

## Completion Criteria

- [x] Single wrapper class used by all GitHub API calls
- [x] Token priority respected: Config → SKILLMEAT env → GITHUB env
- [x] Settings page shows config file value
- [x] All existing tests pass (GitHub-related tests)
- [x] Build succeeds
