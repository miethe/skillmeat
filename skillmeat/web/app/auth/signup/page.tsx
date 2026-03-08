/**
 * Signup Page
 *
 * Renders Clerk's SignUp component when auth is enabled.
 * Redirects to home when auth is disabled (zero-auth mode).
 *
 * Note: SignUp is imported directly from @clerk/nextjs because it is a
 * Clerk-specific UI component, not auth logic. Our abstraction in @/lib/auth
 * covers auth state/hooks/context — Clerk UI components are an acceptable
 * direct import at the page level.
 */

import { redirect } from 'next/navigation';

const AUTH_ENABLED = process.env['NEXT_PUBLIC_AUTH_ENABLED'] === 'true';

export const metadata = {
  title: 'Sign Up',
};

export default function SignupPage() {
  if (!AUTH_ENABLED) {
    redirect('/');
  }

  // Dynamically import Clerk's SignUp so it is never evaluated when auth is disabled.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { SignUp } = require('@clerk/nextjs') as typeof import('@clerk/nextjs');

  return (
    <div className="flex w-full justify-center">
      <SignUp />
    </div>
  );
}
