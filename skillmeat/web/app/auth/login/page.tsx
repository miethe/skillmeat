/**
 * Login Page
 *
 * Renders Clerk's SignIn component when auth is enabled.
 * Redirects to home when auth is disabled (zero-auth mode).
 *
 * Note: SignIn is imported directly from @clerk/nextjs because it is a
 * Clerk-specific UI component, not auth logic. Our abstraction in @/lib/auth
 * covers auth state/hooks/context — Clerk UI components are an acceptable
 * direct import at the page level.
 */

import { redirect } from 'next/navigation';

const AUTH_ENABLED = process.env['NEXT_PUBLIC_AUTH_ENABLED'] === 'true';

export const metadata = {
  title: 'Sign In',
};

export default function LoginPage() {
  if (!AUTH_ENABLED) {
    redirect('/');
  }

  // Dynamically import Clerk's SignIn so it is never evaluated when auth is disabled.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { SignIn } = require('@clerk/nextjs') as typeof import('@clerk/nextjs');

  return (
    <div className="flex w-full justify-center">
      <SignIn />
    </div>
  );
}
