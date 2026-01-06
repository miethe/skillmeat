# Quick Feature: Collapsible Directory Mappings

## Status: completed

## Description
Make the "Directory Mappings" section collapsible on marketplace source detail pages. When mappings exist, show a compact "View Mappings" button next to the status badges. When expanded, display the full section with a collapse button.

## Requirements
1. Only show when `source.manual_map` has entries (existing condition)
2. Collapsed state: Button beneath status badges showing "View Mappings (N)"
3. Expanded state: Current Card implementation with collapse button at top
4. Use existing Collapsible pattern from `excluded-list.tsx`
5. Default to collapsed to reduce visual noise

## Files to Modify
- `skillmeat/web/app/marketplace/sources/[id]/page.tsx` - Replace Card with Collapsible

## Pattern Reference
- Existing pattern: `components/excluded-list.tsx` uses Radix `Collapsible`
- Imports: `@/components/ui/collapsible`
- Icons: `ChevronDown`, `ChevronUp` from `lucide-react`

## Implementation
1. Add `useState` for `isMappingsOpen` (default: false)
2. Wrap Directory Mappings in `Collapsible` component
3. Collapsed trigger: Button with "View Mappings (count)" and chevron
4. Expanded content: Existing Card with collapse button added to header

## Quality Gates
- [x] TypeScript compiles (no new errors - pre-existing test file issues only)
- [x] ESLint passes (no new errors - pre-existing warnings only)
- [ ] Visual testing in browser
