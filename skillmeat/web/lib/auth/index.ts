/**
 * Auth abstraction barrel export.
 *
 * ALL components and hooks should import from here, never from:
 *   - @clerk/nextjs directly
 *   - ./clerk-provider directly
 *
 * This ensures Clerk is never a direct dependency of application code.
 */

export type { AuthUser, AuthProvider } from './types';
export { AuthContextProvider, useAuth, useAuthUser } from './auth-context';
export { NoopAuthWrapper, noopAuthProvider } from './noop-provider';

// Re-export the wrapper component for use in layout.tsx
export { AuthWrapper } from './wrapper';

// Auth-aware fetch utility for use in hooks and components
export { useAuthFetch } from './api-helpers';
