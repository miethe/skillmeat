'use client';

import { useCallback } from 'react';
import { useAuth } from './auth-context';

/**
 * Hook that returns a fetch function with auth headers injected.
 *
 * Uses our auth abstraction — never Clerk directly.
 *
 * In zero-auth mode (isEnabled === false), getToken() returns null and no
 * Authorization header is added. Existing behaviour is preserved.
 *
 * Usage in hooks:
 *   const fetchWithAuth = useAuthFetch();
 *   const data = await fetchWithAuth('/some/url', { method: 'POST', body: ... });
 *
 * For hooks that use the central apiRequest / apiRequestWithHeaders utilities,
 * prefer calling buildApiHeaders({ Authorization: `Bearer ${token}` }) with a
 * token retrieved via `auth.getToken()` instead of replacing the fetch layer.
 */
export function useAuthFetch() {
  const auth = useAuth();

  return useCallback(
    async (url: string, options?: RequestInit): Promise<Response> => {
      const token = await auth.getToken();
      const headers = new Headers(options?.headers);

      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      return fetch(url, { ...options, headers });
    },
    [auth]
  );
}
