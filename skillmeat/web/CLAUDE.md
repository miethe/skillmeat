# CLAUDE.md - Web Frontend

Next.js 15 frontend for SkillMeat web interface

## Architecture

**Stack**: Next.js 15 (App Router) + React 19 + TypeScript + Radix UI + shadcn + TanStack Query

```
web/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Home page
│   ├── globals.css             # Global styles
│   ├── collection/             # Collection browser
│   ├── projects/               # Project management
│   ├── marketplace/            # Claude marketplace
│   ├── mcp/                    # MCP servers
│   ├── settings/               # Settings
│   └── sharing/                # Sharing features
├── components/                 # React components
│   ├── ui/                     # shadcn primitives
│   ├── shared/                 # Shared components
│   ├── collection/             # Collection-specific
│   ├── dashboard/              # Dashboard widgets
│   ├── marketplace/            # Marketplace UI
│   └── providers.tsx           # Context providers
├── lib/                        # Utilities
│   ├── api.ts                  # API client
│   └── utils.ts                # Helper functions
├── sdk/                        # Generated API client (OpenAPI)
│   ├── models/                 # TypeScript types
│   ├── services/               # API service classes
│   └── SkillMeatClient.ts      # Main client
├── types/                      # TypeScript type definitions
│   ├── artifact.ts
│   ├── project.ts
│   ├── analytics.ts
│   └── marketplace.ts
├── hooks/                      # Custom React hooks
├── __tests__/                  # Unit tests (Jest)
└── tests/                      # E2E tests (Playwright)
```

---

## Development

### Commands

| Command | Purpose |
|---------|---------|
| `pnpm dev` | Start dev server (port 3000) |
| `pnpm build` | Build for production |
| `pnpm start` | Start production server |
| `pnpm lint` | Run ESLint |
| `pnpm type-check` | Run TypeScript checks |
| `pnpm test` | Run unit tests |
| `pnpm test:e2e` | Run E2E tests |
| `pnpm clean` | Clean .next directory |

### Environment Variables

**File**: `.env.local` (gitignored)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8080
NEXT_PUBLIC_API_VERSION=v1
NEXT_PUBLIC_API_KEY=your-api-key
NEXT_PUBLIC_API_TOKEN=your-token
NEXT_PUBLIC_ENABLE_API_MOCKS=false
NEXT_PUBLIC_API_TRACE=false
```

---

## App Router Structure

**Pattern**: File-system based routing (Next.js 15)

### Root Layout

**File**: `app/layout.tsx`

```tsx
import { Providers } from '@/components/providers';
import { Header } from '@/components/header';
import { Navigation } from '@/components/navigation';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="flex h-screen flex-col">
            <Header />
            <div className="flex flex-1 overflow-hidden">
              <Navigation />
              <main className="flex-1 overflow-auto">{children}</main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
```

### Page Components

**File**: `app/collection/page.tsx`

```tsx
import { CollectionBrowser } from '@/components/collection/collection-browser';

export default async function CollectionPage() {
  return (
    <div className="container mx-auto py-6">
      <h1 className="text-3xl font-bold">Collection</h1>
      <CollectionBrowser />
    </div>
  );
}
```

### Dynamic Routes

**File**: `app/projects/[id]/page.tsx`

```tsx
export default async function ProjectPage({ params }: { params: { id: string } }) {
  const { id } = await params;
  return <ProjectDetails projectId={id} />;
}
```

---

## API Client

### Configuration

**File**: `lib/api.ts`

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

export const apiConfig = {
  baseUrl: API_BASE_URL,
  version: API_VERSION,
  apiKey: process.env.NEXT_PUBLIC_API_KEY,
  apiToken: process.env.NEXT_PUBLIC_API_TOKEN,
};

export class ApiError extends Error {
  status: number;
  body?: unknown;

  constructor(message: string, status: number, body?: unknown) {
    super(message);
    this.status = status;
    this.body = body;
  }
}
```

### Fetch Wrapper

```typescript
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = buildApiUrl(path);
  const headers = {
    'Content-Type': 'application/json',
    ...(apiConfig.apiToken && { Authorization: `Bearer ${apiConfig.apiToken}` }),
    ...options?.headers,
  };

  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.statusText, response.status, body);
  }

  return response.json();
}
```

### Generated SDK

**Generate from OpenAPI**:

```bash
pnpm generate-sdk
```

**Usage**:

```typescript
import { SkillMeatClient } from '@/sdk';

const client = new SkillMeatClient({
  BASE: apiConfig.baseUrl,
  TOKEN: apiConfig.apiToken,
});

// Use generated methods
const artifacts = await client.artifacts.listArtifacts();
const project = await client.projects.getProject(projectId);
```

---

## Data Fetching

### TanStack Query (React Query)

**Setup** (`components/providers.tsx`):

```tsx
'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000, // 5 minutes
        retry: 1,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

### Custom Hooks

**File**: `hooks/use-artifacts.ts`

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { SkillMeatClient } from '@/sdk';

export function useArtifacts() {
  return useQuery({
    queryKey: ['artifacts'],
    queryFn: async () => {
      const client = new SkillMeatClient(apiConfig);
      return client.artifacts.listArtifacts();
    },
  });
}

export function useCreateArtifact() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: ArtifactCreateRequest) => {
      const client = new SkillMeatClient(apiConfig);
      return client.artifacts.createArtifact(data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
    },
  });
}
```

**Usage in Components**:

```tsx
'use client';

import { useArtifacts, useCreateArtifact } from '@/hooks/use-artifacts';

export function ArtifactList() {
  const { data, isLoading, error } = useArtifacts();
  const createArtifact = useCreateArtifact();

  if (isLoading) return <Spinner />;
  if (error) return <ErrorAlert error={error} />;

  return (
    <div>
      {data?.artifacts.map(artifact => (
        <ArtifactCard key={artifact.id} artifact={artifact} />
      ))}
      <CreateArtifactButton onSubmit={createArtifact.mutate} />
    </div>
  );
}
```

---

## Components

### Component Structure

**Pattern**: Feature-based organization

```
components/
├── ui/                         # Primitives (shadcn)
│   ├── button.tsx
│   ├── dialog.tsx
│   ├── input.tsx
│   └── ...
├── shared/                     # Shared across features
│   ├── error-boundary.tsx
│   ├── loading-spinner.tsx
│   └── empty-state.tsx
├── collection/                 # Collection-specific
│   ├── collection-browser.tsx
│   ├── artifact-card.tsx
│   └── artifact-actions.tsx
└── dashboard/                  # Dashboard widgets
    ├── usage-chart.tsx
    └── recent-activity.tsx
```

### shadcn/ui Components

**Install Component**:

```bash
pnpm dlx shadcn@latest add button
pnpm dlx shadcn@latest add dialog
pnpm dlx shadcn@latest add input
```

**Usage**:

```tsx
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader } from '@/components/ui/dialog';

export function CreateArtifactDialog({ open, onOpenChange }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>Create Artifact</DialogHeader>
        <ArtifactForm />
        <Button type="submit">Create</Button>
      </DialogContent>
    </Dialog>
  );
}
```

### Custom Components

**File**: `components/collection/artifact-card.tsx`

```tsx
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Artifact } from '@/types/artifact';

interface ArtifactCardProps {
  artifact: Artifact;
  onSelect?: (artifact: Artifact) => void;
}

export function ArtifactCard({ artifact, onSelect }: ArtifactCardProps) {
  return (
    <Card className="cursor-pointer hover:shadow-md" onClick={() => onSelect?.(artifact)}>
      <CardHeader>
        <CardTitle>{artifact.name}</CardTitle>
        <Badge variant="secondary">{artifact.artifact_type}</Badge>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{artifact.source}</p>
      </CardContent>
    </Card>
  );
}
```

---

## Styling

### Tailwind CSS

**Config**: `tailwind.config.js`

```javascript
module.exports = {
  darkMode: ["class"],
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        // ... shadcn color system
      },
    },
  },
  plugins: [require("tailwindcss-animate"), require("@tailwindcss/typography")],
};
```

### Global Styles

**File**: `app/globals.css`

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    /* ... CSS variables */
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    /* ... dark mode variables */
  }
}
```

### Utility Function

**File**: `lib/utils.ts`

```typescript
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Usage**:

```tsx
<div className={cn("base-class", isActive && "active-class", className)} />
```

---

## TypeScript Types

### Type Definitions

**File**: `types/artifact.ts`

```typescript
export type ArtifactType = 'skill' | 'command' | 'agent' | 'mcp' | 'hook';
export type ScopeType = 'user' | 'local';

export interface Artifact {
  id: string;
  name: string;
  artifact_type: ArtifactType;
  source: string;
  version: string;
  scope: ScopeType;
  aliases: string[];
  created_at: string;
  updated_at: string;
}

export interface ArtifactCreateRequest {
  name: string;
  artifact_type: ArtifactType;
  source: string;
  version?: string;
  scope?: ScopeType;
  aliases?: string[];
}
```

### Type Safety

```typescript
// Use generated SDK types when possible
import type { ArtifactResponse } from '@/sdk/models';

// Or define custom types for UI-specific data
interface ArtifactCardProps {
  artifact: ArtifactResponse;
  variant?: 'default' | 'compact';
  onSelect?: (artifact: ArtifactResponse) => void;
}
```

---

## Testing

### Unit Tests (Jest + React Testing Library)

**File**: `__tests__/components/artifact-card.test.tsx`

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { ArtifactCard } from '@/components/collection/artifact-card';

describe('ArtifactCard', () => {
  const mockArtifact = {
    id: '1',
    name: 'test-skill',
    artifact_type: 'skill' as const,
    source: 'user/repo/skill',
    version: '1.0.0',
    scope: 'user' as const,
    aliases: [],
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  it('renders artifact name', () => {
    render(<ArtifactCard artifact={mockArtifact} />);
    expect(screen.getByText('test-skill')).toBeInTheDocument();
  });

  it('calls onSelect when clicked', () => {
    const onSelect = jest.fn();
    render(<ArtifactCard artifact={mockArtifact} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('test-skill'));
    expect(onSelect).toHaveBeenCalledWith(mockArtifact);
  });
});
```

**Run Tests**:

```bash
pnpm test
pnpm test:watch
pnpm test:coverage
```

### E2E Tests (Playwright)

**File**: `tests/collection.spec.ts`

```typescript
import { test, expect } from '@playwright/test';

test.describe('Collection Page', () => {
  test('displays artifacts', async ({ page }) => {
    await page.goto('/collection');
    await expect(page.getByRole('heading', { name: 'Collection' })).toBeVisible();
    await expect(page.getByTestId('artifact-list')).toBeVisible();
  });

  test('creates new artifact', async ({ page }) => {
    await page.goto('/collection');
    await page.click('button:has-text("Create Artifact")');
    await page.fill('input[name="name"]', 'test-skill');
    await page.selectOption('select[name="artifact_type"]', 'skill');
    await page.fill('input[name="source"]', 'user/repo/skill');
    await page.click('button:has-text("Submit")');
    await expect(page.getByText('test-skill')).toBeVisible();
  });
});
```

**Run E2E Tests**:

```bash
pnpm test:e2e
pnpm test:e2e:ui      # Interactive mode
pnpm test:e2e:debug   # Debug mode
```

---

## Performance

### Code Splitting

Next.js automatically code-splits by route. For additional optimization:

```tsx
import dynamic from 'next/dynamic';

// Lazy load heavy components
const CodeEditor = dynamic(() => import('@/components/editor/code-editor'), {
  loading: () => <Skeleton />,
  ssr: false,
});
```

### Image Optimization

```tsx
import Image from 'next/image';

<Image
  src="/artifact-icon.png"
  alt="Artifact icon"
  width={48}
  height={48}
  priority={false}
/>
```

### Caching Strategy

```typescript
// TanStack Query config
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,  // 5 minutes
      cacheTime: 10 * 60 * 1000,  // 10 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
```

---

## Key Patterns

### Server vs Client Components

```tsx
// Server Component (default)
export default async function Page() {
  const data = await fetch('...');  // Can fetch directly
  return <div>{data}</div>;
}

// Client Component (use 'use client')
'use client';
import { useState } from 'react';

export function InteractiveComponent() {
  const [state, setState] = useState(false);
  return <button onClick={() => setState(!state)}>Toggle</button>;
}
```

### Form Handling

```tsx
'use client';
import { useForm } from 'react-hook-form';

interface FormData {
  name: string;
  source: string;
}

export function ArtifactForm() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>();

  const onSubmit = (data: FormData) => {
    console.log(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('name', { required: true })} />
      {errors.name && <span>Name is required</span>}
      <button type="submit">Submit</button>
    </form>
  );
}
```

### Error Boundaries

```tsx
'use client';
import { ErrorBoundary as ReactErrorBoundary } from 'react-error-boundary';

function ErrorFallback({ error }: { error: Error }) {
  return <div>Error: {error.message}</div>;
}

export function ErrorBoundary({ children }: { children: React.ReactNode }) {
  return (
    <ReactErrorBoundary FallbackComponent={ErrorFallback}>
      {children}
    </ReactErrorBoundary>
  );
}
```

---

## Important Notes

- **App Router**: Use Next.js 15 App Router patterns (not Pages Router)
- **Server Components**: Default to server components; use 'use client' sparingly
- **React 19**: Leverages concurrent features; avoid unnecessary useEffect
- **Radix UI**: Unstyled primitives; style with Tailwind + shadcn
- **Type Safety**: Use generated SDK types; avoid `any`
- **Accessibility**: All interactive elements keyboard-navigable
- **Performance**: Monitor bundle size; lazy load when appropriate
- **Testing**: Unit tests for logic, E2E tests for critical flows
- **Dark Mode**: Support via Tailwind dark: variant
