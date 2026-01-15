# Testing Rules

<!-- Path Scope: skillmeat/web/__tests__/**/*.ts, skillmeat/web/__tests__/**/*.tsx, skillmeat/web/tests/**/*.ts -->

Testing patterns for SkillMeat frontend.

## Test Types

| Type | Location | Runner |
|------|----------|--------|
| Unit/Integration | `__tests__/` | Jest + RTL |
| E2E | `tests/` | Playwright |

## Commands

| Command | Purpose |
|---------|---------|
| `pnpm test` | Run all unit tests |
| `pnpm test:watch` | Watch mode |
| `pnpm test:coverage` | With coverage |
| `pnpm test:e2e` | E2E headless |

## Query Priority (RTL)

Use in this order:
1. `getByRole` - buttons, links, headings
2. `getByLabelText` - form inputs
3. `getByText` - non-interactive text
4. `getByTestId` - **last resort only**

## Critical Patterns

- **Async**: Use `waitFor()` or `findBy` queries
- **Interactions**: `userEvent.setup()` over `fireEvent`
- **TanStack Query**: Fresh `QueryClient` per test with `retry: false`

## Coverage Requirements

| Metric | Target |
|--------|--------|
| Statements | >80% |
| Branches | >75% |

## Detailed Reference

For test templates, mock patterns, E2E examples:
**Read**: `.claude/context/key-context/testing-patterns.md`
