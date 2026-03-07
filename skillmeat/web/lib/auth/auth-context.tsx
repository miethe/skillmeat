'use client';

import React, { createContext, useContext } from 'react';
import type { AuthProvider, AuthUser } from './types';

const AuthContext = createContext<AuthProvider | null>(null);

/**
 * Provides the active AuthProvider to the component tree.
 * Used internally by auth wrapper components.
 */
export function AuthContextProvider({
  provider,
  children,
}: {
  provider: AuthProvider;
  children: React.ReactNode;
}): React.ReactElement {
  return <AuthContext.Provider value={provider}>{children}</AuthContext.Provider>;
}

/**
 * Returns the current AuthProvider from context.
 * Must be called inside a component tree wrapped by an auth wrapper.
 */
export function useAuth(): AuthProvider {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error('useAuth must be used within an auth wrapper (AuthContextProvider)');
  }
  return ctx;
}

/**
 * Convenience hook that returns the current user or null.
 */
export function useAuthUser(): AuthUser | null {
  const auth = useAuth();
  return auth.getUser();
}
