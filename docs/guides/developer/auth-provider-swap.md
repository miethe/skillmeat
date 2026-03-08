---
title: Swapping Auth Providers
created: 2026-03-07
updated: 2026-03-07
scope: Frontend auth abstraction layer
audience: AI agents and developers implementing new auth providers
---

# Swapping Auth Providers

SkillMeat's frontend auth is behind a pluggable `AuthProvider` interface. Clerk is the current implementation, but the system is designed so that switching to Auth0, Supabase Auth, Firebase Auth, or a custom provider requires **no changes** to components, hooks, pages, or API client code.

## Architecture

```
lib/auth/
  types.ts            # AuthProvider + AuthUser interfaces (STABLE CONTRACT)
  auth-context.tsx     # React context + useAuth() / useAuthUser() hooks
  wrapper.tsx          # Selects provider based on NEXT_PUBLIC_AUTH_ENABLED
  index.ts             # Barrel export (only public surface)
  clerk-provider.tsx   # Clerk implementation (only file importing @clerk/nextjs)
  noop-provider.tsx    # Zero-auth local mode
  api-helpers.ts       # useAuthFetch() hook for token injection
```

**Enforcement boundary**: Only `clerk-provider.tsx` imports from `@clerk/nextjs`. All application code imports from `@/lib/auth`.

**Known exceptions** (edge runtime — React context unavailable):
- `middleware.ts` — imports `@clerk/nextjs/server` directly
- `app/auth/login/page.tsx` — imports Clerk `SignIn` UI component
- `app/auth/signup/page.tsx` — imports Clerk `SignUp` UI component

## Step-by-step: Adding a New Provider

### 1. Implement the AuthProvider interface

Create `lib/auth/NEW-provider.tsx`:

```typescript
'use client';

import React from 'react';
import type { AuthProvider, AuthUser } from './types';

// --- Provider implementation ---

class NewAuthProvider implements AuthProvider {
  isEnabled = true;

  getUser(): AuthUser | null {
    // Map the provider's user object to AuthUser
    // Return null if not signed in
  }

  isAuthenticated(): boolean {
    // Return true if user has a valid session
  }

  async getToken(): Promise<string | null> {
    // Return a JWT or access token for API calls
    // This token is injected into Authorization headers by useAuthFetch()
  }

  async signOut(): Promise<void> {
    // Clear session, redirect to login
  }

  async switchOrganization(orgId: string): Promise<void> {
    // Switch active workspace/tenant
    // If the provider doesn't support orgs, this can be a no-op
  }
}

// --- Wrapper component ---

// This component initializes the provider SDK and makes the AuthProvider
// instance available to the React tree.

export function NewAuthWrapper({ children }: { children: React.ReactNode }) {
  // Wrap children in the provider's SDK context (e.g., <Auth0Provider>)
  return <SdkProvider>{children}</SdkProvider>;
}

// --- Bridge component ---

// Bridges the provider's React hooks into our AuthProvider instance.
// Uses a render-prop pattern so the wrapper.tsx can inject it into AuthContextProvider.

export function NewAuthProviderBridge({
  children,
}: {
  children: (provider: AuthProvider) => React.ReactElement;
}) {
  // Use the provider's hooks here to build the AuthProvider instance
  const provider = new NewAuthProvider(/* pass hook values */);
  return children(provider);
}
```

### 2. Wire it into wrapper.tsx

Update `lib/auth/wrapper.tsx` to select the new provider:

```typescript
// Add a new branch based on env var or provider name
const AUTH_PROVIDER = process.env['NEXT_PUBLIC_AUTH_PROVIDER'] || 'clerk';

export function AuthWrapper({ children }: { children: React.ReactNode }) {
  if (!AUTH_ENABLED) {
    return (
      <NoopAuthWrapper>
        <AuthContextProvider provider={noopAuthProvider}>{children}</AuthContextProvider>
      </NoopAuthWrapper>
    );
  }

  switch (AUTH_PROVIDER) {
    case 'new-provider':
      return <NewAuthWrapperWithContext>{children}</NewAuthWrapperWithContext>;
    case 'clerk':
    default:
      return <ClerkAuthWrapperWithContext>{children}</ClerkAuthWrapperWithContext>;
  }
}

function NewAuthWrapperWithContext({ children }: { children: React.ReactNode }) {
  const { NewAuthWrapper, NewAuthProviderBridge } = require('./new-provider');
  const { AuthContextProvider: Ctx } = require('./auth-context');

  return (
    <NewAuthWrapper>
      <NewAuthProviderBridge>
        {(provider) => <Ctx provider={provider}>{children}</Ctx>}
      </NewAuthProviderBridge>
    </NewAuthWrapper>
  );
}
```

### 3. Update middleware.ts

Replace the Clerk middleware import with the new provider's equivalent:

```typescript
// middleware.ts
function buildNewProviderMiddleware() {
  // Use the new provider's server-side auth middleware
  // Must protect routes and redirect unauthenticated users to /auth/login
}
```

This is one of the files that imports the provider SDK directly (edge runtime constraint). Document the exception with a comment.

### 4. Update auth pages

Replace Clerk's `SignIn`/`SignUp` components in `app/auth/login/page.tsx` and `app/auth/signup/page.tsx` with the new provider's UI components — or build custom forms that call the provider's auth methods.

### 5. Update environment variables

Add the new provider's env vars to `.env.local` and `.env.example`. Add `NEXT_PUBLIC_AUTH_PROVIDER=new-provider` to select it.

### 6. Remove old provider (optional)

Once the new provider is verified, you can remove `clerk-provider.tsx` and uninstall `@clerk/nextjs`. No other files need to change.

## What you do NOT need to touch

| Layer | Why |
|-------|-----|
| Components using `useAuth()` / `useAuthUser()` | They consume the interface, not the implementation |
| `WorkspaceSwitcher` | Calls `auth.switchOrganization()` — provider-agnostic |
| `UserProfile` | Reads `AuthUser` fields — same interface regardless of provider |
| `useAuthFetch()` / `api-helpers.ts` | Calls `auth.getToken()` — works with any provider |
| `buildApiHeaders()` in `lib/api.ts` | Accepts a token string — doesn't know where it came from |
| E2E tests (zero-auth suite) | Tests zero-auth mode which uses `noop-provider` |
| Backend API (`require_auth` dependency) | Validates JWT — doesn't care which frontend SDK issued it |

## AuthUser interface reference

```typescript
interface AuthUser {
  id: string;
  email: string | null;
  name: string | null;
  imageUrl: string | null;
  organizationId: string | null;   // current workspace/tenant
  organizations: Array<{
    id: string;
    name: string;
    role: string;
  }>;
}
```

If the new provider doesn't support organizations, set `organizationId: null` and `organizations: []`. The `WorkspaceSwitcher` returns `null` when the list is empty.

## Testing a new provider

1. Set env vars for the new provider
2. Set `NEXT_PUBLIC_AUTH_ENABLED=true` and `NEXT_PUBLIC_AUTH_PROVIDER=new-provider`
3. Run `pnpm dev` and verify login/signup flows
4. Check that API calls include `Authorization: Bearer <token>` in browser devtools
5. Verify workspace switching (if applicable)
6. Run `pnpm test:e2e -- tests/auth.e2e.ts` for zero-auth regression
7. Run auth-enabled E2E tests against a sandbox instance
