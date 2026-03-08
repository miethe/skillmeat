'use client';

import React from 'react';
import type { AuthProvider, AuthUser } from './types';

const LOCAL_ADMIN_USER: AuthUser = {
  id: 'local_admin',
  email: 'local@skillmeat.local',
  name: 'Local Admin',
  imageUrl: null,
  organizationId: null,
  organizations: [{ id: 'local', name: 'Local', role: 'system_admin' }],
};

/**
 * No-op auth provider for local/zero-auth mode.
 * Returns a static local_admin user; never loads Clerk SDK.
 */
export const noopAuthProvider: AuthProvider = {
  isEnabled: false,

  getUser(): AuthUser {
    return LOCAL_ADMIN_USER;
  },

  isAuthenticated(): boolean {
    return true;
  },

  async getToken(): Promise<null> {
    return null;
  },

  async signOut(): Promise<void> {
    // No-op in local mode
  },

  async switchOrganization(_orgId: string): Promise<void> {
    // No-op in local mode
  },
};

/**
 * Wrapper component for no-op mode. Simply renders children as-is.
 */
export function NoopAuthWrapper({ children }: { children: React.ReactNode }): React.ReactElement {
  return <>{children}</>;
}
