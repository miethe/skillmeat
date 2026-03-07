'use client';

import React from 'react';
import { AuthContextProvider } from './auth-context';
import { NoopAuthWrapper, noopAuthProvider } from './noop-provider';

const AUTH_ENABLED = process.env['NEXT_PUBLIC_AUTH_ENABLED'] === 'true';

/**
 * Primary auth wrapper component.
 * Reads NEXT_PUBLIC_AUTH_ENABLED at runtime and selects the appropriate provider.
 *
 * Use this directly in layout.tsx — it handles both auth-enabled and noop paths.
 */
export function AuthWrapper({ children }: { children: React.ReactNode }): React.ReactElement {
  if (!AUTH_ENABLED) {
    return (
      <NoopAuthWrapper>
        <AuthContextProvider provider={noopAuthProvider}>{children}</AuthContextProvider>
      </NoopAuthWrapper>
    );
  }

  return <ClerkAuthWrapperWithContext>{children}</ClerkAuthWrapperWithContext>;
}

/**
 * Clerk-backed wrapper — only rendered when NEXT_PUBLIC_AUTH_ENABLED=true.
 * Dynamically requires Clerk to ensure zero Clerk SDK initialization when auth is disabled.
 */
function ClerkAuthWrapperWithContext({
  children,
}: {
  children: React.ReactNode;
}): React.ReactElement {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ClerkAuthWrapper, ClerkAuthProviderBridge } = require('./clerk-provider') as typeof import('./clerk-provider');
  const { AuthContextProvider: Ctx } = require('./auth-context') as typeof import('./auth-context');

  return (
    <ClerkAuthWrapper>
      <ClerkAuthProviderBridge>
        {(provider) => <Ctx provider={provider}>{children}</Ctx>}
      </ClerkAuthProviderBridge>
    </ClerkAuthWrapper>
  );
}
