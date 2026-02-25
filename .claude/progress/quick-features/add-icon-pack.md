---
feature: add-icon-pack
status: in-progress
branch: feat/color-icon-management
created: 2026-02-25
updated: '2026-02-25'
---

# Add Icon Pack Feature

## Overview
Add a '+' button to the Icons Settings page that lets users install new icon packs
via URL download or file upload. Includes progress indication and post-install messaging.

## Design Decisions
- **URL mode**: Backend fetches the URL (avoids CORS issues on frontend)
- **File upload**: Client sends raw JSON, backend validates and stores
- **Progress**: In-dialog loading spinner (indeterminate — no byte-level progress)
- **Post-install**: Toast notification + TanStack Query cache invalidation (no hard reload needed)
- **Pack format**: JSON `{id, name, icons: [{name, label?}]}` — Lucide icon name references
- **Storage**: Pack definitions stored in `icon-packs.config.json` alongside existing packs

## Files

### Backend
| File | Change |
|------|--------|
| `skillmeat/api/schemas/icon_packs.py` | Add `IconPackInstallRequest`, `IconPackInstallUrlRequest` schemas |
| `skillmeat/api/routers/icon_packs.py` | Add `POST /settings/icon-packs/install` (URL + file upload) and `DELETE /settings/icon-packs/{pack_id}` |

### Frontend
| File | Change |
|------|--------|
| `skillmeat/web/lib/api/icon-packs.ts` | Add `installIconPackFromUrl`, `installIconPackFromFile` functions |
| `skillmeat/web/hooks/use-icon-packs.ts` | Add `useInstallIconPack` mutation hook |
| `skillmeat/web/app/settings/components/icons-settings.tsx` | Add '+' button + `AddIconPackDialog` component |

## Tasks

- [x] TASK-1: Backend schemas + install endpoint
- [x] TASK-2: Frontend API client + hook
- [x] TASK-3: Frontend AddIconPackDialog + '+' button in settings

## Notes
- Sonner toast: use `toast.promise()` for async operation feedback
- Progress: use `isPending` state in dialog (spinner + disabled inputs)
- Post-install: `queryClient.invalidateQueries({ queryKey: iconPackKeys.all })`
- Show info alert in success state: "Pack installed — icon picker updated automatically"
