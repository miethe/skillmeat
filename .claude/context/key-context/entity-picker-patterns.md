# Entity Picker Patterns

When to use the `EntityPickerDialog` component system and how to extend it.

## File Locations

| Component | File |
|-----------|------|
| `EntityPickerDialog`, `EntityPickerTrigger` | `components/shared/entity-picker-dialog.tsx` |
| Adapter hooks | `components/shared/entity-picker-adapter-hooks.ts` |
| `MiniContextEntityCard` | `components/context/mini-context-entity-card.tsx` |

## When to Use

**Use EntityPickerDialog** when users need to browse many entities with infinite scroll, rich card display, search, or type filtering.

**Keep ArtifactPicker / ContextModulePicker** when a compact popover suffices (< ~20 items, tight layouts).

## Current Integration Points

| Location | Mode | allowedTypes | typeFilters | File:Lines |
|----------|------|-------------|-------------|------------|
| Stage Editor — Primary Agent | single | `['agent']` | none | `workflow/stage-editor.tsx:488-511` |
| Stage Editor — Supporting Tools | multi | `['skill','command','mcp']` | Skills, Commands, MCP Servers | `workflow/stage-editor.tsx:514-539` |
| Builder Sidebar — Global Modules | multi | none | none | `workflow/builder-sidebar.tsx:536-553` |

## allowedTypes vs typeFilters

`EntityPickerTab` separates two distinct filtering concerns:

| Field | Who controls it | Purpose |
|-------|----------------|---------|
| `allowedTypes` | Tab definition (developer) | Base type constraint. Limits which entity types can ever appear. |
| `typeFilters` | End user (pill clicks) | Narrows within allowedTypes. Optional per-tab. |

**How the effective filter is computed** (in `TabContent`):
- User has active pills → pass pill selection to `useData.typeFilter`
- No active pills, `allowedTypes` set → pass `allowedTypes` to `useData.typeFilter`
- No active pills, no `allowedTypes` → pass `undefined` (all types visible)

**Convention**: `typeFilters` values must be a subset of `allowedTypes`. The dialog does not enforce this at runtime — misconfigured tabs (e.g. a "Hooks" pill on a tab with `allowedTypes: ['skill']`) would show 0 results for that pill since the API filters to the pill value, but other pills would still work.

**`useData` is now a passthrough** — with `allowedTypes` handling base restriction, `useData` implementations should just forward `params` without overriding `typeFilter`:
```typescript
// ✓ Correct — let allowedTypes + dialog handle filtering
useData: (params) => useEntityPickerArtifacts(params),

// ✗ Wrong — overrides the computed effective filter
useData: (params) => useEntityPickerArtifacts({ ...params, typeFilter: ['skill'] }),
```

## Key Gotcha: useData is a Hook

`EntityPickerTab.useData` is called as a React hook by `TabContent` internally. ESLint cannot detect this statically.

**Rules**:
- Define tab configs inside `useMemo` for stable references
- Never call `useData` conditionally or inside callbacks
- Tab order must remain stable between renders

See JSDoc on `useData` field in `entity-picker-dialog.tsx:54-65` for full explanation.

## Creating a New Adapter Hook

To integrate a new entity type:

1. Create a hook returning `InfiniteDataResult<T>` (interface defined in `entity-picker-dialog.tsx:29-37`)
2. For paginated sources: flatten `data.pages` into `items` array
3. For non-paginated sources: set `hasNextPage: false`, `fetchNextPage: () => {}` — see `useEntityPickerContextModules` as reference
4. Wire into a tab config — see `stage-editor.tsx:352-373` for live examples
5. Add `allowedTypes` to restrict which entity types this tab shows — the dialog applies it automatically. Add `typeFilters` if users should be able to narrow further.

## Accessibility (Built-in)

All a11y is handled by the dialog component — no per-integration work needed:
- Focus trap (Radix Dialog), arrow-key grid nav, ARIA listbox/option roles
- Live announcement region, checkmark overlay (WCAG color-not-alone)

## See Also

- Live usage examples: `workflow/stage-editor.tsx`, `workflow/builder-sidebar.tsx`
- Source patterns: `deployment-sets/add-member-dialog.tsx` (original extracted from)
- General component conventions: `.claude/context/key-context/component-patterns.md`
