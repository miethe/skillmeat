# Bug Fixes - November 2025

## Summary

Bug fixes resolved during November 2025.

---

### Web Build Clean Script Fails on pnpm Symlinks

**Issue**: `pnpm build:fresh` fails when cleaning `.next` directory due to nested pnpm symlinks in `.next/standalone/node_modules/.pnpm/` causing "Directory not empty" errors on macOS.

- **Location**: `skillmeat/web/package.json:11-13`
- **Root Cause**: pnpm creates complex symlink structures inside the Next.js standalone build output. On macOS, `rm -rf` can fail on these nested symlink directories when file permissions or locks prevent immediate deletion.
- **Fix**: Enhanced clean scripts to retry with permission fix if initial `rm -rf` fails:
  - `clean`: Attempts `rm -rf`, falls back to `chmod -R u+w` then retry, always succeeds
  - `clean:cache`: Same pattern for cache-only cleanup
  - `clean:all`: Same pattern for full cleanup including node_modules
- **Commit(s)**: `cb8e14c`
- **Status**: RESOLVED

---

### Custom API Port Not Applied to Frontend

**Issue**: Running `skillmeat web dev --api-port 8080 --web-port 3001` starts the API on port 8080, but the frontend continues making requests to port 8000.

- **Location**: `skillmeat/web/manager.py:151-155`
- **Root Cause**: The WebManager's `_get_web_config()` method only set the `PORT` environment variable for Next.js but never set `NEXT_PUBLIC_API_URL`. Without this variable, the frontend fell back to hardcoded defaults (inconsistently 8000 or 8080 across different modules).
- **Fix**:
  1. Added `NEXT_PUBLIC_API_URL` environment variable in `manager.py` using the configured `api_host` and `api_port`
  2. Unified the environment variable name from `NEXT_PUBLIC_API_BASE_URL` to `NEXT_PUBLIC_API_URL` in `sdk/core/OpenAPI.ts`
  3. Standardized fallback port to 8080 in `app/settings/page.tsx` for consistency with `lib/api.ts`
- **Commit(s)**: `b10af74`
- **Status**: RESOLVED

---

### Missing EntityLifecycleProvider in Project Detail Page

**Issue**: Clicking into a project from the projects list causes React error: "useEntityLifecycle must be used within EntityLifecycleProvider"

- **Location**: `skillmeat/web/app/projects/[id]/page.tsx:366-370`
- **Root Cause**: The ProjectDetailPage component renders UnifiedEntityModal which internally calls useEntityLifecycle hook, but the page did not wrap its content in EntityLifecycleProvider. When users clicked on a deployed artifact to view details, the modal attempted to access the context and threw an error.
- **Fix**:
  1. Added import for EntityLifecycleProvider from '@/components/entity/EntityLifecycleProvider' (line 22)
  2. Wrapped entire page return JSX with `<EntityLifecycleProvider mode="project" projectPath={project?.path}>` (lines 179-374)
  3. Pattern matches other project pages like `/projects/[id]/manage/page.tsx`
- **Commit(s)**: `TBD`
- **Status**: RESOLVED
