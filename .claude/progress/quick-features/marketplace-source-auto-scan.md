---
type: quick-feature-plan
feature_slug: marketplace-source-auto-scan
request_log_id: REQ-20260104-skillmeat-01
status: in-progress
created: 2026-01-04T19:30:00Z
estimated_scope: medium
---

# Marketplace Sources: Auto-scan on add + Smart URL inference

## Scope

Two enhancements to /marketplace/sources/ flow:
1. Auto-scan on source addition - trigger scan immediately when adding, auto-refresh UI
2. Smart URL auto-import - single URL input that infers repo structure from GitHub URLs

## Affected Files

### Backend
- `skillmeat/api/routers/marketplace_sources.py`: Add auto-scan trigger in create_source, add URL inference endpoint
- `skillmeat/api/schemas/marketplace.py`: Add AutoImportRequest schema with URL inference fields

### Frontend
- `skillmeat/web/components/marketplace/add-source-modal.tsx`: Restructure with auto-import section + separator
- `skillmeat/web/hooks/useMarketplaceSources.ts`: Add useAutoImportSource mutation

## Implementation Steps

1. **Backend: Auto-scan trigger** → @python-backend-engineer
   - Modify `create_source()` to call scan logic after creation
   - Return scan result in response (or trigger async scan)
   - Update scan_status appropriately

2. **Backend: URL inference endpoint** → @python-backend-engineer
   - Add `POST /marketplace/sources/infer-url` endpoint
   - Parse GitHub URLs like `https://github.com/owner/repo/tree/branch/path`
   - Return inferred: repo_url, ref (branch/tag), root_hint (subdirectory)
   - Handle various GitHub URL formats

3. **Frontend: Modal UI restructure** → @ui-engineer-enhanced
   - Add auto-import section at top with single URL input
   - Add "Or" separator between auto-import and manual entry
   - Keep shared fields at bottom (frontmatter detection, trust level)
   - Show loading/inference state when URL is entered

4. **Frontend: Hook integration** → @ui-engineer-enhanced
   - Add `useInferUrl()` mutation to call inference endpoint
   - Modify `useCreateSource` to handle auto-scan response
   - Ensure proper cache invalidation after scan completes

## Testing
- Test URL inference with various GitHub URL formats
- Test auto-scan triggers and completes on source add
- Test UI shows scan results without manual refresh
- Test fallback to manual entry when inference fails

## Completion Criteria
- [ ] Adding source via auto-import triggers immediate scan
- [ ] UI updates automatically when scan completes
- [ ] URL inference works for standard GitHub tree URLs
- [ ] Manual entry fields still work as before
- [ ] Error handling for failed inference shows helpful message
- [ ] Build and tests pass
