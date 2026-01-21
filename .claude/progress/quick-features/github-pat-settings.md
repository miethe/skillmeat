---
type: quick-feature-plan
feature_slug: github-pat-settings
request_log_id: null
status: completed
created: 2026-01-17T00:00:00Z
completed_at: 2026-01-17T19:43:00Z
estimated_scope: medium
---

# GitHub PAT Settings

## Scope

Add a GitHub Personal Access Token (PAT) settings section to the /settings page that allows users to optionally authenticate with GitHub, improving API rate limits from 60 req/hr to 5000 req/hr. The PAT is stored securely in ConfigManager and used by all GitHub API calls centrally.

## Affected Files

### New Files
- `skillmeat/api/routers/settings.py`: New router with POST/GET/DELETE endpoints for PAT management
- `skillmeat/api/schemas/settings.py`: Pydantic schemas for settings requests/responses
- `skillmeat/web/lib/api/settings.ts`: Frontend API client functions
- `skillmeat/web/components/settings/github-settings.tsx`: GitHub PAT form component

### Modified Files
- `skillmeat/api/server.py`: Register settings router
- `skillmeat/web/app/settings/page.tsx`: Add GitHubSettings component
- `skillmeat/web/lib/api/index.ts`: Export settings module

## Implementation Steps

1. Backend: Create schemas for PAT management → @python-backend-engineer
2. Backend: Create settings router with 4 endpoints → @python-backend-engineer
3. Backend: Register router in server.py → @python-backend-engineer
4. Frontend: Create settings API client → @ui-engineer
5. Frontend: Create GitHubSettings component → @ui-engineer
6. Frontend: Update settings page and exports → @ui-engineer

## Testing

- Format validation (token starts with "ghp_")
- GitHub API validation via test call
- ConfigManager persistence
- UI set/clear/status display
- Environment variable fallback works
- Rate limit verification

## Completion Criteria

- [x] PAT endpoints working (set/get/delete/validate)
- [x] Frontend component renders and functions
- [x] Token stored securely in ConfigManager
- [x] Validation against GitHub API
- [x] Tests pass
- [x] Build succeeds

## Related Enhancement

GitHub App authentication support captured as REQ-20260117-skillmeat-01.
