---
type: context
schema_version: 2
doc_type: context
prd: "color-icon-management"
feature_slug: "color-icon-management"
created: 2026-02-25
updated: 2026-02-25
---

# Color & Icon Management — Context

## Feature Overview

Unify color and icon selection across Groups and Deployment Sets with API-backed persistence, shared components, and shadcn-iconpicker integration.

## Key Files

### Backend
- `skillmeat/cache/models.py` — CustomColor model (new), DeploymentSet model (add color/icon columns)
- `skillmeat/cache/repositories.py` — CustomColorRepository (new)
- `skillmeat/api/routers/colors.py` — Colors CRUD API (new)
- `skillmeat/api/routers/deployment_sets.py` — Uncomment color/icon persistence
- `skillmeat/api/schemas/colors.py` — Color DTOs (new)
- `skillmeat/api/schemas/deployment_sets.py` — Existing, verify color/icon fields

### Frontend
- `skillmeat/web/components/shared/color-selector.tsx` — Shared color picker (new)
- `skillmeat/web/components/shared/icon-picker.tsx` — Shared icon picker wrapping shadcn-iconpicker (new)
- `skillmeat/web/lib/color-constants.ts` — Shared color types/helpers (new, extracted from group-constants)
- `skillmeat/web/lib/icon-constants.ts` — Shared icon types/helpers (new)
- `skillmeat/web/lib/group-constants.ts` — Update to re-export from new constants files
- `skillmeat/web/hooks/colors.ts` — React Query hooks for colors API (new)
- `skillmeat/web/hooks/icon-packs.ts` — React Query hooks for icon packs API (new)
- `skillmeat/web/app/groups/components/group-metadata-editor.tsx` — Refactor to use shared components
- `skillmeat/web/components/deployment-sets/create-deployment-set-dialog.tsx` — Use shared components
- `skillmeat/web/components/deployment-sets/edit-deployment-set-dialog.tsx` — Use shared components
- `skillmeat/web/app/settings/page.tsx` — Add Appearance tab
- `skillmeat/web/app/settings/components/appearance-settings.tsx` — New
- `skillmeat/web/app/settings/components/colors-settings.tsx` — New
- `skillmeat/web/app/settings/components/icons-settings.tsx` — New

### Config
- `skillmeat/web/config/icon-packs.config.json` — Icon pack definitions (new)

## Technical Decisions

- shadcn-iconpicker installed via shadcn CLI (copies into components/ui/)
- Custom colors stored in DB via API (replacing localStorage)
- localStorage migration: one-time banner on first Settings visit
- Icon packs configurable via JSON config file
- All color/icon mutations invalidate React Query caches for real-time updates

## Dependencies

- shadcn-iconpicker: `pnpm dlx shadcn@latest add "https://icon-picker.alan-courtois.fr/r/icon-picker"`
- @uiw/react-color-sketch: Already used in group-metadata-editor
- fuse.js, @tanstack/react-virtual: Required by shadcn-iconpicker
