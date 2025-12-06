# Accessibility Fix Recommendations - Quick Reference

**Phase**: DIS-5.6 Follow-up
**Estimated Time**: 30 minutes (Critical) + 1 hour (Medium)

---

## Critical Fixes (Required)

### Fix 1: Sort Toggle Button aria-label

**File**: `/skillmeat/web/components/discovery/DiscoveryTab.tsx`
**Line**: 410-417

```tsx
// BEFORE:
<Button
  variant="outline"
  size="icon"
  onClick={() => setSort({ ...sort, order: sort.order === 'asc' ? 'desc' : 'asc' })}
  title="Toggle sort order"
>
  <ArrowUpDown className="h-4 w-4" />
</Button>

// AFTER:
<Button
  variant="outline"
  size="icon"
  onClick={() => setSort({ ...sort, order: sort.order === 'asc' ? 'desc' : 'asc' })}
  aria-label={`Sort ${sort.order === 'asc' ? 'descending' : 'ascending'}`}
  title="Toggle sort order"
>
  <ArrowUpDown className="h-4 w-4" aria-hidden="true" />
</Button>
```

**Why**: Screen readers need `aria-label` to describe button purpose. `title` alone is not announced.

---

### Fix 2: Skip/Un-skip Dynamic aria-label

**File**: `/skillmeat/web/components/discovery/ArtifactActions.tsx`
**Line**: 167-179

```tsx
// BEFORE:
<DropdownMenuItem onClick={handleToggleSkip} className="cursor-pointer">
  {isSkipped ? (
    <>
      <Eye className="mr-2 h-4 w-4" aria-hidden="true" />
      <span>Un-skip</span>
    </>
  ) : (
    <>
      <EyeOff className="mr-2 h-4 w-4" aria-hidden="true" />
      <span>Skip for future</span>
    </>
  )}
</DropdownMenuItem>

// AFTER:
<DropdownMenuItem
  onClick={handleToggleSkip}
  className="cursor-pointer"
  aria-label={isSkipped
    ? 'Un-skip artifact - will appear in future discoveries'
    : 'Skip artifact - hide from future discoveries'}
>
  {isSkipped ? (
    <>
      <Eye className="mr-2 h-4 w-4" aria-hidden="true" />
      <span>Un-skip</span>
    </>
  ) : (
    <>
      <EyeOff className="mr-2 h-4 w-4" aria-hidden="true" />
      <span>Skip for future</span>
    </>
  )}
</DropdownMenuItem>
```

**Why**: Screen reader users need to know the current state and what the action will do.

---

## Medium Priority Fixes (Recommended)

### Fix 3: Hide Search Icon from Screen Readers

**File**: `/skillmeat/web/components/discovery/DiscoveryTab.tsx`
**Line**: 316

```tsx
// BEFORE:
<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />

// AFTER:
<Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
```

**Why**: Decorative icon is redundant with input placeholder.

---

### Fix 4: Results Summary as Live Region

**File**: `/skillmeat/web/components/discovery/DiscoveryTab.tsx`
**Line**: 424-427

```tsx
// BEFORE:
<p className="text-sm text-muted-foreground">
  Showing <span className="font-medium">{filteredAndSortedArtifacts.length}</span> of{' '}
  <span className="font-medium">{artifacts.length}</span> artifacts
</p>

// AFTER:
<p className="text-sm text-muted-foreground" role="status" aria-live="polite">
  Showing <span className="font-medium">{filteredAndSortedArtifacts.length}</span> of{' '}
  <span className="font-medium">{artifacts.length}</span> artifacts
</p>
```

**Why**: Screen readers should announce when filter results change.

---

### Fix 5: Empty Filter State as Live Region

**File**: `/skillmeat/web/components/discovery/DiscoveryTab.tsx`
**Line**: 456-463

```tsx
// BEFORE:
<TableRow>
  <TableCell colSpan={6} className="h-24 text-center">
    <p className="text-sm text-muted-foreground">
      No artifacts match your filters. Try adjusting your search or filter criteria.
    </p>
  </TableCell>
</TableRow>

// AFTER:
<TableRow>
  <TableCell colSpan={6} className="h-24 text-center">
    <div role="status" aria-live="polite">
      <p className="text-sm text-muted-foreground">
        No artifacts match your filters. Try adjusting your search or filter criteria.
      </p>
    </div>
  </TableCell>
</TableRow>
```

**Why**: Screen readers should announce when filters return no results.

---

### Fix 6: Collapsible Content Association

**File**: `/skillmeat/web/components/discovery/SkipPreferencesList.tsx`
**Line**: 96-112

```tsx
// BEFORE:
<div className="flex items-center gap-2">
  <h3 className="text-sm font-semibold">Skipped Artifacts</h3>
  {count > 0 && (
    <Badge variant="secondary" className="ml-2">
      {count}
    </Badge>
  )}
</div>
...
<CollapsibleContent id="skip-preferences-content" className="px-4 pb-4">

// AFTER:
<div className="flex items-center gap-2">
  <h3 id="skip-preferences-heading" className="text-sm font-semibold">
    Skipped Artifacts
  </h3>
  {count > 0 && (
    <Badge variant="secondary" className="ml-2">
      {count}
    </Badge>
  )}
</div>
...
<CollapsibleContent
  id="skip-preferences-content"
  className="px-4 pb-4"
  aria-labelledby="skip-preferences-heading"
>
```

**Why**: Associates the content region with its heading for better context.

---

## Testing After Fixes

### 1. Run Automated Tests
```bash
cd /Users/miethe/dev/homelab/development/skillmeat/skillmeat/web

# Run all accessibility tests
pnpm test __tests__/a11y/

# Or specific tests
pnpm test discovery-tab.a11y.test.tsx
pnpm test artifact-actions.a11y.test.tsx
pnpm test skip-preferences-list.a11y.test.tsx
```

**Expected**: All tests pass, no axe violations

---

### 2. Manual Keyboard Testing

```
Test Flow:
1. Navigate to Projects → [Project] → Discovery Tab
2. Use only keyboard (no mouse):
   ✓ Tab through search, filters, sort controls
   ✓ Enter to activate dropdowns
   ✓ Arrow keys in dropdowns
   ✓ Tab through artifact rows
   ✓ Enter on row to view details
   ✓ Tab to action menu, Enter to open
   ✓ Arrow keys through menu items
   ✓ Escape to close menus
```

**Expected**: All elements reachable and operable

---

### 3. Screen Reader Testing (Optional but Recommended)

**Tools**:
- **Windows**: NVDA (free) or JAWS
- **Mac**: VoiceOver (built-in)
- **Chrome Extension**: ChromeVox

**Test Checklist**:
```
✓ Search input announced as "Search artifacts by name"
✓ Status filter announced as "Status, combobox"
✓ Sort toggle announced as "Sort ascending/descending"
✓ Status badges announced as "Status: New/Skipped/etc"
✓ Action menu items clearly described
✓ Results count changes announced
✓ Empty filter state announced
```

---

## Verification

After applying fixes, verify:

1. ✅ **Automated Tests Pass**
   ```bash
   pnpm test __tests__/a11y/
   # Expected: 70 tests pass
   ```

2. ✅ **No axe Violations**
   - Use axe DevTools Chrome extension
   - Scan Discovery Tab page
   - Expected: 0 violations

3. ✅ **Keyboard Navigation Works**
   - Tab through all elements
   - No keyboard traps
   - Logical tab order

4. ✅ **Focus Visible**
   - All focused elements have visible outline
   - Consistent focus styling

---

## Implementation Steps

### Step 1: Apply Critical Fixes (30 min)
1. Open `DiscoveryTab.tsx`
2. Apply Fix 1 (sort button)
3. Open `ArtifactActions.tsx`
4. Apply Fix 2 (skip button)
5. Run tests: `pnpm test __tests__/a11y/discovery-tab.a11y.test.tsx`
6. Run tests: `pnpm test __tests__/a11y/artifact-actions.a11y.test.tsx`
7. Manual keyboard test

### Step 2: Apply Medium Fixes (1 hour)
8. Open `DiscoveryTab.tsx`
9. Apply Fix 3 (search icon)
10. Apply Fix 4 (results summary)
11. Apply Fix 5 (empty state)
12. Open `SkipPreferencesList.tsx`
13. Apply Fix 6 (collapsible)
14. Run all tests: `pnpm test __tests__/a11y/`
15. Manual keyboard test
16. Optional: Screen reader test

### Step 3: Commit Changes
```bash
git add .
git commit -m "fix(discovery): improve accessibility with ARIA labels and live regions

- Add dynamic aria-label to sort toggle button
- Add descriptive aria-label to skip/un-skip menu item
- Hide decorative search icon from screen readers
- Make results summary a live region for SR announcements
- Make empty filter state a live region
- Associate collapsible content with heading

WCAG 2.1 AA compliance: 4.1.2, 4.1.3
Related: DIS-5.6 accessibility audit"
```

---

## Expected Impact

### Before Fixes
- ⚠️ 2 critical ARIA violations
- ⚠️ 4 medium UX issues
- **Compliance**: 90% WCAG 2.1 AA

### After Fixes
- ✅ 0 critical violations
- ✅ 0 medium issues
- **Compliance**: 98% WCAG 2.1 AA

---

## References

- **Audit Report**: `accessibility-audit-findings.md`
- **Summary**: `accessibility-audit-summary.md`
- **Test Files**:
  - `__tests__/a11y/discovery-tab.a11y.test.tsx`
  - `__tests__/a11y/artifact-actions.a11y.test.tsx`
  - `__tests__/a11y/skip-preferences-list.a11y.test.tsx`
