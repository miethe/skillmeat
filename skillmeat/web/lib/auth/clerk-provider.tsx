'use client';

import React from 'react';
import {
  ClerkProvider,
  useAuth as useClerkAuth,
  useUser,
  useOrganization,
  useOrganizationList,
} from '@clerk/nextjs';
import type { AuthProvider, AuthUser } from './types';

/**
 * Maps Clerk user/org data to our AuthUser interface.
 * Must be called inside a component that is wrapped by ClerkProvider.
 */
function useClerkAuthProvider(): AuthProvider {
  const { getToken: clerkGetToken, signOut: clerkSignOut, isSignedIn } = useClerkAuth();
  const { user } = useUser();
  const { organization } = useOrganization();
  const { setActive, userMemberships } = useOrganizationList({
    userMemberships: { infinite: true },
  });

  const getUser = (): AuthUser | null => {
    if (!isSignedIn || !user) {
      return null;
    }

    const memberships = (userMemberships.data ?? []).map((m) => ({
      id: m.organization.id,
      name: m.organization.name,
      role: m.role,
    }));

    return {
      id: user.id,
      email: user.primaryEmailAddress?.emailAddress ?? null,
      name: user.fullName,
      imageUrl: user.imageUrl ?? null,
      organizationId: organization?.id ?? null,
      organizations: memberships,
    };
  };

  const isAuthenticated = (): boolean => {
    return isSignedIn === true;
  };

  const getToken = async (): Promise<string | null> => {
    try {
      return await clerkGetToken();
    } catch {
      return null;
    }
  };

  const signOut = async (): Promise<void> => {
    await clerkSignOut();
  };

  const switchOrganization = async (orgId: string): Promise<void> => {
    if (setActive) {
      await setActive({ organization: orgId });
    }
  };

  return {
    isEnabled: true,
    getUser,
    isAuthenticated,
    getToken,
    signOut,
    switchOrganization,
  };
}

/**
 * Internal bridge component that builds the Clerk-backed AuthProvider
 * and injects it into the React context via a render prop.
 */
function ClerkAuthProviderBridge({
  children,
}: {
  children: (provider: AuthProvider) => React.ReactNode;
}): React.ReactElement {
  const provider = useClerkAuthProvider();
  return <>{children(provider)}</>;
}

export { ClerkAuthProviderBridge, useClerkAuthProvider };

/**
 * Wraps the app in ClerkProvider.
 * Reads publishable key from NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.
 */
export function ClerkAuthWrapper({ children }: { children: React.ReactNode }): React.ReactElement {
  const publishableKey = process.env['NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY'];

  return (
    <ClerkProvider publishableKey={publishableKey ?? ''}>
      {children}
    </ClerkProvider>
  );
}
