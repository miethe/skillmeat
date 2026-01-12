<!-- Path Scope: skillmeat/web/__tests__/**/*.ts, skillmeat/web/__tests__/**/*.tsx, skillmeat/web/tests/**/*.ts -->

# Web Frontend Testing - Patterns and Best Practices

Testing patterns for SkillMeat web frontend using Jest, React Testing Library, and Playwright.

---

## Test Types

| Type | Location | Purpose | Runner |
|------|----------|---------|--------|
| Unit/Integration | `__tests__/` | Components, hooks, utils | Jest + RTL |
| E2E | `tests/` | Full user workflows | Playwright |

---

## Unit Tests (Jest + React Testing Library)

### File Structure

```
__tests__/
├── components/
│   ├── CollectionCard.test.tsx
│   └── GroupList.test.tsx
├── hooks/
│   └── use-collections.test.ts
└── lib/
    └── api.test.ts
```

**Naming**: `[module-name].test.ts(x)`

### Test Commands

| Command | Purpose |
|---------|---------|
| `pnpm test` | Run all unit tests |
| `pnpm test:watch` | Watch mode for development |
| `pnpm test:coverage` | Run with coverage report |
| `pnpm test:ci` | CI mode (no watch, coverage) |

### Component Test Template

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CollectionCard } from '@/components/collection-card';

describe('CollectionCard', () => {
  it('renders collection name and description', () => {
    const collection = {
      id: '1',
      name: 'Test Collection',
      description: 'Test description',
    };

    render(<CollectionCard collection={collection} />);

    // Use accessible queries (getByRole, getByText)
    expect(screen.getByRole('heading', { name: 'Test Collection' })).toBeInTheDocument();
    expect(screen.getByText('Test description')).toBeInTheDocument();
  });

  it('handles click events', async () => {
    const user = userEvent.setup();
    const onClick = jest.fn();

    render(<CollectionCard collection={...} onClick={onClick} />);

    await user.click(screen.getByRole('button', { name: 'View' }));
    expect(onClick).toHaveBeenCalledWith('1');
  });
});
```

### Testing Hooks with TanStack Query

```typescript
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCollections } from '@/hooks';

// Mock API client
jest.mock('@/lib/api/collections', () => ({
  fetchCollections: jest.fn(),
}));

import { fetchCollections } from '@/lib/api/collections';

describe('useCollections', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },  // Disable retries in tests
      },
    });
    jest.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  it('fetches collections successfully', async () => {
    const mockCollections = [{ id: '1', name: 'Test' }];
    (fetchCollections as jest.Mock).mockResolvedValueOnce(mockCollections);

    const { result } = renderHook(() => useCollections(), { wrapper });

    // Wait for query to complete
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockCollections);
    expect(fetchCollections).toHaveBeenCalledTimes(1);
  });

  it('handles errors', async () => {
    (fetchCollections as jest.Mock).mockRejectedValueOnce(new Error('API error'));

    const { result } = renderHook(() => useCollections(), { wrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toEqual(new Error('API error'));
  });
});
```

### Mocking Fetch

```typescript
// Mock global fetch
global.fetch = jest.fn();

beforeEach(() => {
  jest.resetAllMocks();
});

it('calls API correctly', async () => {
  const mockData = { id: '1', name: 'Test' };

  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => mockData,
  });

  const result = await fetchCollection('1');

  expect(result).toEqual(mockData);
  expect(global.fetch).toHaveBeenCalledWith(
    'http://localhost:8080/api/v1/collections/1'
  );
});
```

---

## E2E Tests (Playwright)

### File Structure

```
tests/
├── collections.spec.ts
├── groups.spec.ts
└── deployments.spec.ts
```

**Naming**: `[feature].spec.ts`

### Test Commands

| Command | Purpose |
|---------|---------|
| `pnpm test:e2e` | Run E2E tests headless |
| `pnpm test:e2e:ui` | Run with Playwright UI |
| `pnpm test:e2e:debug` | Run in debug mode |
| `pnpm test:e2e:codegen` | Generate test code |

### E2E Test Template

```typescript
import { test, expect } from '@playwright/test';

test.describe('Collections', () => {
  test('creates new collection', async ({ page }) => {
    // Navigate
    await page.goto('http://localhost:3000');

    // Interact
    await page.getByRole('button', { name: 'New Collection' }).click();
    await page.getByLabel('Name').fill('My Collection');
    await page.getByLabel('Description').fill('Test description');
    await page.getByRole('button', { name: 'Create' }).click();

    // Assert
    await expect(page.getByText('My Collection')).toBeVisible();
    await expect(page.getByText('Collection created successfully')).toBeVisible();
  });

  test('navigates to collection details', async ({ page }) => {
    await page.goto('http://localhost:3000');

    await page.getByRole('link', { name: 'My Collection' }).click();

    await expect(page).toHaveURL(/\/collections\/[a-f0-9-]+/);
    await expect(page.getByRole('heading', { name: 'My Collection' })).toBeVisible();
  });
});
```

---

## Best Practices

### Query Priority (React Testing Library)

Use accessible queries in this order:

1. **`getByRole`** - Most accessible (buttons, links, headings)
   ```typescript
   screen.getByRole('button', { name: 'Submit' })
   screen.getByRole('heading', { name: 'Title' })
   ```

2. **`getByLabelText`** - Form inputs
   ```typescript
   screen.getByLabelText('Email')
   ```

3. **`getByPlaceholderText`** - Fallback for inputs
   ```typescript
   screen.getByPlaceholderText('Enter name')
   ```

4. **`getByText`** - Non-interactive text
   ```typescript
   screen.getByText('Success message')
   ```

5. **`getByTestId`** - Last resort only
   ```typescript
   screen.getByTestId('custom-widget')
   ```

### Async Testing

```typescript
// ✅ GOOD: Use waitFor for async assertions
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});

// ✅ GOOD: Use findBy queries (built-in waitFor)
const element = await screen.findByText('Loaded');

// ❌ BAD: No waiting for async operations
expect(screen.getByText('Loaded')).toBeInTheDocument();
```

### User Interactions

```typescript
import userEvent from '@testing-library/user-event';

// ✅ GOOD: Use userEvent for realistic interactions
const user = userEvent.setup();
await user.click(button);
await user.type(input, 'text');

// ❌ BAD: Use fireEvent (less realistic)
fireEvent.click(button);
```

---

## Common Antipatterns

❌ **Testing implementation details**:
```typescript
// BAD: Testing internal state
expect(component.state.count).toBe(1);
```

✅ **Test user-visible behavior**:
```typescript
// GOOD: Test what user sees
expect(screen.getByText('Count: 1')).toBeInTheDocument();
```

❌ **Skipping accessibility queries**:
```typescript
// BAD: Using testId first
screen.getByTestId('submit-button')
```

✅ **Use semantic queries**:
```typescript
// GOOD: Use accessible role
screen.getByRole('button', { name: 'Submit' })
```

❌ **No cleanup between tests**:
```typescript
// BAD: Shared mutable state
let queryClient = new QueryClient();

beforeEach(() => {
  // No reset
});
```

✅ **Proper setup/teardown**:
```typescript
// GOOD: Fresh instance per test
beforeEach(() => {
  queryClient = new QueryClient();
  jest.clearAllMocks();
});
```

❌ **Hardcoded waits**:
```typescript
// BAD: Arbitrary timeout
await new Promise(resolve => setTimeout(resolve, 1000));
```

✅ **Condition-based waiting**:
```typescript
// GOOD: Wait for specific condition
await waitFor(() => expect(result.current.isSuccess).toBe(true));
```

---

## Coverage Requirements

| Metric | Target |
|--------|--------|
| Statements | >80% |
| Branches | >75% |
| Functions | >80% |
| Lines | >80% |

**Check coverage**:
```bash
pnpm test:coverage
# Open coverage/lcov-report/index.html
```

---

## Reference

- **Jest**: https://jestjs.io/
- **React Testing Library**: https://testing-library.com/react
- **Playwright**: https://playwright.dev/
- **Query Priorities**: https://testing-library.com/docs/queries/about/#priority
