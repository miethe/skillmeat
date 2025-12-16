# Accessibility Audit: Context Entities UI
**Date**: 2025-12-15
**Target**: WCAG 2.1 AA Compliance
**Scope**: Context entities components in `skillmeat/web/components/context/`

---

## Executive Summary

**Status**: 7 Critical Issues, 12 Medium Issues, 5 Low Issues
**Compliance**: Currently ~60% WCAG 2.1 AA compliant
**Estimated Effort**: 4-6 hours to reach full compliance

---

## Critical Issues (Must Fix)

### 1. Missing ARIA Labels on Icon-Only Buttons
**Severity**: Critical (WCAG 4.1.2)
**Files**: `context-entity-card.tsx`, `context-entity-detail.tsx`

**Issue**: Icon-only buttons lack accessible names:
- Edit button (Pencil icon) - line 287
- Delete button (Trash2 icon) - line 299
- Close button in detail (X icon) - line 338
- Toggle content view button - line 221

**Current Code**:
```tsx
<Button variant="ghost" size="icon" onClick={handleEdit}>
  <Pencil className="h-4 w-4" />
</Button>
```

**Impact**: Screen reader users cannot identify button purpose.

**Fix Required**: Add `aria-label` to all icon-only buttons.

---

### 2. Dialog Not Keyboard Dismissible
**Severity**: Critical (WCAG 2.1.1)
**Files**: `context-entity-detail.tsx`, `deploy-to-project-dialog.tsx`

**Issue**: Dialogs use Radix Dialog which should handle Esc key, but `handleClose` logic may prevent it.

**Current Code** (deploy-to-project-dialog.tsx:109):
```tsx
<Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
```

**Impact**: Keyboard users cannot dismiss dialog with Esc key during loading states.

**Fix Required**: Ensure Esc key works in all states (except when explicitly blocked).

---

### 3. Missing Focus Trap in Editor Dialog
**Severity**: Critical (WCAG 2.4.3)
**Files**: `context-entity-editor.tsx`

**Issue**: Editor renders in page context, not as modal. No focus trap implemented.

**Impact**: Tab key allows focus to escape editor, confusing keyboard users.

**Fix Required**: Wrap editor in Dialog component with proper focus management.

---

### 4. Select Dropdown Items Missing Descriptions for Screen Readers
**Severity**: Critical (WCAG 1.3.1)
**Files**: `context-entity-editor.tsx` (line 260-265)

**Issue**: Entity type select shows description visually but not to screen readers.

**Current Code**:
```tsx
<SelectItem key={option.value} value={option.value}>
  <div>
    <div className="font-medium">{option.label}</div>
    <div className="text-xs text-muted-foreground">{option.description}</div>
  </div>
</SelectItem>
```

**Impact**: Screen reader users miss important context about each entity type.

**Fix Required**: Add `aria-describedby` or include description in accessible name.

---

### 5. Form Validation Errors Not Announced
**Severity**: Critical (WCAG 3.3.1)
**Files**: `context-entity-editor.tsx`

**Issue**: Error messages appear visually but lack ARIA live region announcements.

**Current Code** (line 214-217):
```tsx
{error && (
  <div className="mb-4 rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
    {error}
  </div>
)}
```

**Impact**: Screen reader users unaware of validation errors.

**Fix Required**: Add `role="alert"` or `aria-live="assertive"`.

---

### 6. Checkbox Labels Not Properly Associated
**Severity**: Critical (WCAG 1.3.1)
**Files**: `context-entity-filters.tsx` (line 97-109)

**Issue**: Checkbox and label not properly connected via `htmlFor` in all cases.

**Impact**: Clicking label may not toggle checkbox; screen reader association unclear.

**Fix Required**: Ensure all checkboxes have matching `id` and `htmlFor`.

---

### 7. Loading States Lack ARIA Announcements
**Severity**: Critical (WCAG 4.1.3)
**Files**: `context-entities/page.tsx`

**Issue**: Loading spinners lack `aria-live` regions to announce state changes.

**Current Code** (line 262-267):
```tsx
{isLoading ? (
  <>
    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
    Loading...
  </>
) : (
  'Load More'
)}
```

**Impact**: Screen reader users unaware content is loading.

**Fix Required**: Add `aria-live="polite"` to loading regions.

---

## Medium Priority Issues

### 8. Hover-Only Actions
**Severity**: Medium (WCAG 2.1.1)
**Files**: `context-entity-card.tsx` (line 280)

**Issue**: Edit/delete buttons only visible on hover (`opacity-0 group-hover:opacity-100`).

**Impact**: Keyboard users may not discover these actions.

**Fix Required**: Make buttons visible on focus or provide keyboard-accessible menu.

---

### 9. Color Alone Conveys Information
**Severity**: Medium (WCAG 1.4.1)
**Files**: `context-entity-card.tsx` (colored borders), `context-load-order.tsx` (green icons)

**Issue**: Auto-load status and entity type indicated only by color.

**Impact**: Colorblind users cannot distinguish entity types.

**Fix Required**: Add icons or text labels in addition to color.

---

### 10. Skip Links Missing
**Severity**: Medium (WCAG 2.4.1)
**Files**: `context-entities/page.tsx`

**Issue**: No skip link to bypass filters and jump to main content.

**Impact**: Keyboard users must tab through all filters to reach content.

**Fix Required**: Add "Skip to results" link at top of page.

---

### 11. Truncated Text Without Full Text Access
**Severity**: Medium (WCAG 1.4.4)
**Files**: `context-entity-card.tsx` (line 242-245), `context-entity-detail.tsx` (line 366)

**Issue**: Truncated path pattern lacks tooltip or full text access.

**Fix Required**: Add `title` attribute or tooltip for truncated text.

---

### 12. Missing Landmark Roles
**Severity**: Medium (WCAG 1.3.1)
**Files**: `context-entities/page.tsx`

**Issue**: Filters sidebar and content area lack landmark roles.

**Impact**: Screen reader users cannot navigate by landmarks.

**Fix Required**: Add `<nav role="search">` for filters, `<main>` for content.

---

### 13. Auto-Load Switch Lacks Context
**Severity**: Medium (WCAG 1.3.1)
**Files**: `context-entity-card.tsx` (line 357-362)

**Issue**: Switch has label but lacks description of what "auto-load" means.

**Impact**: Users may not understand what enabling auto-load does.

**Fix Required**: Add `aria-describedby` pointing to help text.

---

### 14. Dialog Title Hierarchy
**Severity**: Medium (WCAG 1.3.1)
**Files**: `context-entity-detail.tsx` (line 135)

**Issue**: Dialog title uses `<DialogTitle>` but may not be proper heading level.

**Impact**: Screen reader users may have unclear document structure.

**Fix Required**: Verify `DialogTitle` renders as `<h2>` (level after page heading).

---

### 15. Empty State Lacks Proper Heading
**Severity**: Medium (WCAG 1.3.1)
**Files**: `context-entities/page.tsx` (line 35)

**Issue**: Empty state uses `<h3>` but may not follow proper heading hierarchy.

**Fix Required**: Ensure heading levels are sequential (h1 → h2 → h3).

---

### 16. Pagination Controls Lack Context
**Severity**: Medium (WCAG 2.4.4)
**Files**: `context-entities/page.tsx` (line 257)

**Issue**: "Load More" button lacks context about what's being loaded.

**Impact**: Screen reader users may not understand purpose.

**Fix Required**: Use more descriptive text like "Load more context entities".

---

### 17. Filter Reset Button Lacks Count
**Severity**: Medium (WCAG 2.4.4)
**Files**: `context-entity-filters.tsx` (line 151)

**Issue**: "Clear Filters" button doesn't indicate how many filters are active.

**Impact**: Users don't know how many filters will be cleared.

**Fix Required**: Update label to "Clear X filters" or add badge.

---

### 18. Badge Colors Insufficient Contrast
**Severity**: Medium (WCAG 1.4.3)
**Files**: Multiple files

**Issue**: Badge text on colored backgrounds may not meet 4.5:1 contrast ratio.

**Impact**: Low vision users may struggle to read badge text.

**Fix Required**: Test contrast ratios for all badge variants.

---

### 19. Tooltip Trigger Not Keyboard Accessible
**Severity**: Medium (WCAG 2.1.1)
**Files**: `context-entity-card.tsx` (multiple tooltips)

**Issue**: Tooltips may not appear on keyboard focus.

**Impact**: Keyboard users miss tooltip content.

**Fix Required**: Ensure tooltips appear on focus, not just hover.

---

## Low Priority Issues

### 20. Missing Language Attributes
**Severity**: Low (WCAG 3.1.2)
**Files**: All components

**Issue**: Code blocks lack `lang` attribute.

**Impact**: Screen readers may mispronounce code.

**Fix Required**: Add `lang="en"` to code examples if needed.

---

### 21. Redundant ARIA Roles
**Severity**: Low (Best Practice)
**Files**: `context-entity-card.tsx` (line 255)

**Issue**: `role="article"` on Card may be redundant with semantic HTML.

**Impact**: None (doesn't harm, but unnecessary).

**Fix Required**: Remove if Card already uses `<article>`.

---

### 22. Focus Indicators May Be Hidden
**Severity**: Low (WCAG 2.4.7)
**Files**: All interactive components

**Issue**: Custom styling may override default focus indicators.

**Impact**: Keyboard users may lose track of focus.

**Fix Required**: Test focus visibility; add custom focus styles if needed.

---

### 23. Form Field Help Text Not Associated
**Severity**: Low (WCAG 1.3.1)
**Files**: `context-entity-editor.tsx` (multiple fields)

**Issue**: Help text below fields lacks `aria-describedby` connection.

**Current Code** (line 300-302):
```tsx
<p className="text-xs text-muted-foreground">
  Must start with <code className="rounded bg-muted px-1 py-0.5">.claude/</code>
</p>
```

**Impact**: Screen readers may not announce help text when field is focused.

**Fix Required**: Add `id` to help text, reference in input's `aria-describedby`.

---

### 24. Loading Skeleton Lacks ARIA Label
**Severity**: Low (WCAG 4.1.2)
**Files**: `context-entity-detail.tsx` (line 57), `page.tsx` (line 48)

**Issue**: Loading skeletons lack accessible names.

**Impact**: Screen readers announce generic "div" or "skeleton".

**Fix Required**: Add `aria-label="Loading content"` to skeleton containers.

---

## Positive Findings (Already Compliant)

✅ Semantic HTML usage (headings, lists, forms)
✅ Form labels properly associated (`htmlFor` and `id`)
✅ Button text is descriptive (where text exists)
✅ Color scheme supports dark mode
✅ Components use Radix UI primitives (mostly accessible)
✅ Proper use of `aria-label` on some interactive elements
✅ Dialog components from Radix include focus management
✅ Switch components properly labeled

---

## Recommended Fixes (Priority Order)

### Phase 1: Critical (Immediate - Day 1)
1. Add ARIA labels to all icon-only buttons
2. Fix dialog keyboard dismissal
3. Add form error announcements
4. Fix checkbox label associations
5. Add loading state announcements

### Phase 2: Keyboard Navigation (Day 2)
6. Implement focus trap in editor
7. Make hover-only actions keyboard accessible
8. Add skip links
9. Ensure tooltips work on keyboard focus

### Phase 3: Color & Contrast (Day 2)
10. Add non-color indicators for status
11. Test and fix badge contrast ratios
12. Add full text access for truncated content

### Phase 4: Structure & Context (Day 3)
13. Add landmark roles
14. Fix heading hierarchy
15. Add `aria-describedby` for switches
16. Improve button labels with context

### Phase 5: Polish (Optional)
17. Add language attributes where needed
18. Remove redundant ARIA
19. Test and enhance focus indicators
20. Add skeleton loading labels

---

## Testing Checklist

### Automated Testing
- [ ] Run axe DevTools on all pages
- [ ] Run Lighthouse accessibility audit
- [ ] Run WAVE browser extension
- [ ] Check with ESLint plugin-jsx-a11y

### Manual Testing
- [ ] Tab through all interactive elements (keyboard-only)
- [ ] Test screen reader (VoiceOver/NVDA)
- [ ] Test with 200% zoom
- [ ] Test in high contrast mode
- [ ] Test color blindness simulation
- [ ] Test with keyboard shortcuts disabled

### Browser Coverage
- [ ] Chrome + ChromeVox
- [ ] Firefox + NVDA
- [ ] Safari + VoiceOver
- [ ] Edge

---

## Component-Specific Notes

### context-entity-card.tsx
- Most violations: icon buttons, hover-only actions, color-only status
- High usage: Appears in grids, critical for main UX
- Fix priority: HIGH

### context-entity-detail.tsx
- Dialog accessibility mostly good (Radix)
- Missing: button labels, content view toggle label
- Fix priority: MEDIUM

### context-entity-editor.tsx
- Form validation errors need announcements
- Help text needs associations
- Select descriptions need accessibility
- Fix priority: HIGH (blocks creation flow)

### context-entity-filters.tsx
- Checkbox labels good
- Missing: filter count on reset button
- Fix priority: LOW

### deploy-to-project-dialog.tsx
- Dialog structure good
- Overwrite warning could be more prominent for screen readers
- Fix priority: LOW (stub implementation)

### context-load-order.tsx
- Visual-only indicators (green icons)
- Good: Legend explains icons
- Fix priority: MEDIUM

### page.tsx
- Missing: skip links, landmarks
- Good: Proper heading structure
- Fix priority: MEDIUM

---

## Implementation Strategy

1. **Create accessibility utilities** (`lib/a11y-utils.ts`):
   - `announceToScreenReader(message: string)`
   - `useSkipLink(targetId: string)`
   - `useFocusTrap(enabled: boolean)`

2. **Update component patterns**:
   - Icon button wrapper with required aria-label
   - Form error announcement hook
   - Loading state announcement hook

3. **Add tests**:
   - Unit tests for ARIA attributes
   - E2E tests for keyboard navigation
   - Axe-core integration tests

4. **Document patterns** in `.claude/rules/web/accessibility.md`

---

## Risk Assessment

**Low Risk**: Most fixes are additive (ARIA labels, announcements)
**Medium Risk**: Focus management changes (test thoroughly)
**High Risk**: None (no breaking changes to functionality)

---

## References

- [WCAG 2.1 AA Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Radix UI Accessibility](https://www.radix-ui.com/primitives/docs/overview/accessibility)
- [shadcn/ui Accessibility](https://ui.shadcn.com/docs/components/accessible)
- [React ARIA Patterns](https://react-spectrum.adobe.com/react-aria/)
