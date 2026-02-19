---
feature: Source Label Refactor on Collection Cards
status: completed
created: 2026-02-16
branch: feat/collection-org
files_affected:
- skillmeat/web/lib/source-utils.ts (NEW - GitHub URL parser)
- skillmeat/web/components/collection/artifact-browse-card.tsx
- skillmeat/web/components/collection/artifact-details-modal.tsx (optional - use shared
  util)
tasks:
- id: SLR-1
  title: Create shared GitHub URL parsing utility
  status: pending
  assigned_to: ui-engineer
- id: SLR-2
  title: Refactor source label in artifact-browse-card.tsx
  status: pending
  assigned_to: ui-engineer
schema_version: 2
doc_type: quick_feature
feature_slug: source-label-refactor
---

## Requirements

1. **Local artifacts**: Display "Local" with current muted foreground color
2. **GitHub artifacts**: Display GitHub icon (lucide-react) + `owner/repo` with a distinct colored font
3. **Clickable**: GitHub source label is a hyperlink opening full source URL in new tab
4. **Shared utility**: Extract `parseGitHubSource()` to `lib/source-utils.ts` for reuse

## Design Decisions

- Use `lucide-react` GitHub icon (already in project dependencies)
- Color: Use `text-muted-foreground` for "Local", a GitHub-appropriate subtle color for GitHub links
- Parse GitHub URLs client-side (no API call needed - simple regex extraction)
- Utility returns `{ owner, repo, fullUrl }` or null for non-GitHub sources

## Implementation Notes

- Card component: `skillmeat/web/components/collection/artifact-browse-card.tsx` lines ~257-258
- Existing source parsing in modal: `artifact-details-modal.tsx` lines ~584-601
- Artifact type has `origin` field ('github' | 'local') and `source` string field
