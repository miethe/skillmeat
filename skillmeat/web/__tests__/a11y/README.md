# Accessibility Testing for SkillMeat Web

This directory contains accessibility tests and audit documentation for the SkillMeat web interface.

## Current Coverage

### Artifact Deletion Dialog (FE-016) ✅

**Component**: `components/entity/artifact-deletion-dialog.tsx`
**Status**: WCAG 2.1 AA Compliant - 0 violations
**Last Audited**: 2024-12-20

#### Test Results
```
✅ 23/23 tests passed
✅ 0 axe-core violations
✅ All acceptance criteria met
```

#### Documentation
- [Accessibility Audit Summary](./ACCESSIBILITY_AUDIT_SUMMARY.md) - Comprehensive audit report
- [Accessibility Checklist](./ACCESSIBILITY_CHECKLIST.md) - Quick reference checklist
- [Task Completion Report](./TASK_FE-016_COMPLETION_REPORT.md) - Task FE-016 summary

#### Test File
- [artifact-deletion-dialog.a11y.test.tsx](./artifact-deletion-dialog.a11y.test.tsx) - 23 comprehensive test cases

---

## Running Accessibility Tests

```bash
# Run all accessibility tests
pnpm test __tests__/a11y/

# Run specific component test
pnpm test __tests__/a11y/artifact-deletion-dialog.a11y.test.tsx

# Run with coverage
pnpm test:coverage -- __tests__/a11y/
```

---

## Test Categories

Each accessibility test suite should cover:

1. **axe-core audit** - Zero violations
2. **ARIA labels** - All elements properly labeled
3. **Keyboard navigation** - Full keyboard support
4. **Color contrast** - WCAG AA compliance (4.5:1 ratio)
5. **Screen reader** - Proper announcements and live regions
6. **Focus management** - Visible indicators and logical order

---

## WCAG 2.1 AA Compliance

All components in this directory must meet WCAG 2.1 Level AA standards:

- **Perceivable**: Text alternatives, adaptable content, distinguishable
- **Operable**: Keyboard accessible, enough time, seizures, navigable
- **Understandable**: Readable, predictable, input assistance
- **Robust**: Compatible with assistive technologies

---

## Tools Used

- **jest-axe v10.0.0** - Automated accessibility testing
- **axe-core v4.10.2 / v4.11.0** - Accessibility engine
- **@testing-library/react v16.0.1** - Component testing
- **@testing-library/user-event v14.5.2** - User interaction simulation

---

## Adding New Accessibility Tests

### Test Template

```typescript
/**
 * Accessibility Tests for [ComponentName] Component
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

describe('[ComponentName] Accessibility', () => {
  it('has no axe violations in default state', async () => {
    const { container } = render(<Component />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('has accessible labels for all form controls', async () => {
    render(<Component />);
    const inputs = screen.getAllByRole('textbox');
    inputs.forEach((input) => {
      expect(input).toHaveAccessibleName();
    });
  });

  it('supports keyboard navigation', async () => {
    render(<Component />);
    const button = screen.getByRole('button');
    button.focus();
    expect(button).toHaveFocus();
  });
});
```

### Coverage Checklist

- [ ] Default state: Zero violations
- [ ] All interactive states (loading, error, disabled)
- [ ] ARIA labels and descriptions
- [ ] Keyboard navigation (Tab, Enter, Space, Escape)
- [ ] Color contrast (light and dark modes)
- [ ] Screen reader announcements (aria-live regions)
- [ ] Focus management (visible indicators, logical order)
- [ ] Mobile touch targets (≥44x44px)

---

## Reference Documentation

- [WCAG 2.1 Quick Reference](https://www.w3.org/WAI/WCAG21/quickref/)
- [Radix UI Accessibility](https://www.radix-ui.com/primitives/docs/overview/accessibility)
- [axe-core Rules](https://github.com/dequelabs/axe-core/blob/develop/doc/rule-descriptions.md)
- [ARIA Authoring Practices](https://www.w3.org/WAI/ARIA/apg/)

---

## Audit History

| Date | Component | Status | Violations | Notes |
|------|-----------|--------|------------|-------|
| 2024-12-20 | Artifact Deletion Dialog | ✅ Pass | 0 | Task FE-016 complete |

---

## Contact

For questions about accessibility testing or WCAG compliance, refer to:
- Project documentation: `docs/dev/`
- Component rules: `.claude/rules/web/`
- Testing guide: `skillmeat/web/CLAUDE.md`
