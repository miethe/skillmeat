/**
 * Next.js Middleware — Route Protection
 *
 * When NEXT_PUBLIC_AUTH_ENABLED=false (default):
 *   Complete pass-through. No Clerk SDK is initialized or imported. All routes
 *   are accessible without authentication.
 *
 * When NEXT_PUBLIC_AUTH_ENABLED=true:
 *   Uses Clerk's clerkMiddleware to protect all routes except the public ones
 *   listed in PUBLIC_ROUTES.
 *
 * Why Clerk is used directly here (documented exception):
 *   Next.js middleware runs at the Edge runtime. Our React-based auth abstraction
 *   (@/lib/auth) is not available in that context. Direct Clerk import in middleware
 *   is intentional and acceptable — it is the only location in the codebase where
 *   this exception applies.
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const AUTH_ENABLED = process.env['NEXT_PUBLIC_AUTH_ENABLED'] === 'true';

const PUBLIC_ROUTES = ['/auth/login', '/auth/signup', '/api/health'];

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some((route) => pathname === route || pathname.startsWith(route + '/'));
}

// ---------------------------------------------------------------------------
// Zero-auth mode: export a no-op middleware so Next.js is satisfied.
// ---------------------------------------------------------------------------
function noopMiddleware(_request: NextRequest): NextResponse {
  return NextResponse.next();
}

// ---------------------------------------------------------------------------
// Auth-enabled mode: protect routes with Clerk.
// ---------------------------------------------------------------------------
function buildClerkMiddleware() {
  // Dynamic import ensures Clerk is never initialized when AUTH_ENABLED=false.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { clerkMiddleware, createRouteMatcher } = require('@clerk/nextjs/server') as typeof import('@clerk/nextjs/server');

  const isProtectedRoute = createRouteMatcher(['/((?!auth|api/health).*)']);

  return clerkMiddleware(async (auth, request) => {
    if (isProtectedRoute(request) && !isPublicRoute(request.nextUrl.pathname)) {
      await auth.protect();
    }
  });
}

// ---------------------------------------------------------------------------
// Export: select the appropriate middleware at module-evaluation time.
// ---------------------------------------------------------------------------
export default AUTH_ENABLED ? buildClerkMiddleware() : noopMiddleware;

export const config = {
  matcher: [
    // Skip Next.js internals and static assets.
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
