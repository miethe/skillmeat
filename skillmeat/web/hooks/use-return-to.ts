/**
 * useReturnTo Hook
 *
 * Manages cross-navigation state preservation for the modal system.
 * Enables seamless navigation between /collection and /manage pages
 * while preserving filter state, scroll position, and modal context.
 *
 * Features:
 * - Serializes origin URL including all current filters
 * - Prevents nested returnTo params (only one level deep)
 * - Supports browser back button navigation
 * - Provides helper for creating return URLs
 *
 * @example Basic usage
 * ```tsx
 * const { hasReturnTo, returnToLabel, navigateBack } = useReturnTo();
 *
 * if (hasReturnTo) {
 *   return <Button onClick={navigateBack}>Return to {returnToLabel}</Button>
 * }
 * ```
 *
 * @example Creating return URLs for navigation
 * ```tsx
 * const { createReturnUrl } = useReturnTo();
 *
 * // Navigate to /manage with returnTo set to current URL
 * const targetUrl = createReturnUrl('/manage', { artifact: 'skill:canvas' });
 * router.push(targetUrl);
 * ```
 */

'use client';

import { useCallback, useMemo } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';

// ============================================================================
// Types
// ============================================================================

export interface UseReturnToOptions {
  /**
   * Whether to use router.back() as fallback when no returnTo is present.
   * Defaults to true.
   */
  fallbackToRouterBack?: boolean;
}

export interface UseReturnToReturn {
  /**
   * The raw returnTo URL from the query params (decoded).
   * Null if no returnTo is present.
   */
  returnTo: string | null;

  /**
   * Whether a returnTo param is present in the current URL.
   */
  hasReturnTo: boolean;

  /**
   * Human-readable label for the return destination.
   * E.g., "Collection", "Manage", or the page name.
   */
  returnToLabel: string;

  /**
   * The current URL (pathname + search params) without the returnTo param.
   * Useful for serializing the current location.
   */
  currentUrl: string;

  /**
   * Creates a URL with the returnTo param set to the current location.
   * Prevents nesting by removing any existing returnTo from the serialized URL.
   *
   * @param targetPath - The destination path (e.g., '/manage')
   * @param additionalParams - Optional additional query params to include
   * @returns The full URL string with returnTo param
   */
  createReturnUrl: (
    targetPath: string,
    additionalParams?: Record<string, string | undefined>
  ) => string;

  /**
   * Navigate back using the returnTo URL or router.back() as fallback.
   * Safe to call even if no returnTo is present.
   */
  navigateBack: () => void;

  /**
   * Check if the returnTo URL points to a specific page.
   *
   * @param pageName - The page path to check (e.g., '/collection', '/manage')
   * @returns True if returnTo points to the specified page
   */
  isReturningTo: (pageName: string) => boolean;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Extract a human-readable label from a URL path.
 */
function getPageLabel(url: string | null): string {
  if (!url) return 'Previous Page';

  try {
    // Handle both full URLs and relative paths
    const pathname = url.startsWith('/')
      ? url.split('?')[0]
      : new URL(url, 'http://localhost').pathname;

    // Ensure pathname is defined
    if (!pathname) return 'Previous Page';

    // Map common paths to friendly names
    switch (pathname) {
      case '/collection':
        return 'Collection';
      case '/manage':
        return 'Health & Sync';
      case '/marketplace':
        return 'Marketplace';
      case '/projects':
        return 'Projects';
      case '/settings':
        return 'Settings';
      default: {
        // Extract last segment and capitalize
        const segments = pathname.split('/').filter(Boolean);
        const segment = segments[segments.length - 1];
        if (segment) {
          return segment.charAt(0).toUpperCase() + segment.slice(1);
        }
        return 'Previous Page';
      }
    }
  } catch {
    return 'Previous Page';
  }
}

// ============================================================================
// Hook
// ============================================================================

/**
 * useReturnTo - Cross-navigation state preservation hook
 *
 * Manages the returnTo query parameter for preserving navigation context
 * when moving between pages (e.g., /collection and /manage).
 *
 * @param options - Configuration options
 * @returns Object with returnTo state and navigation helpers
 */
export function useReturnTo(options: UseReturnToOptions = {}): UseReturnToReturn {
  const { fallbackToRouterBack = true } = options;

  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // Get the returnTo param from URL
  const returnTo = useMemo(() => {
    const encoded = searchParams.get('returnTo');
    if (!encoded) return null;

    try {
      // Handle both encoded and non-encoded values
      return decodeURIComponent(encoded);
    } catch {
      return encoded;
    }
  }, [searchParams]);

  const hasReturnTo = !!returnTo;

  // Get human-readable label for the return destination
  const returnToLabel = useMemo(() => getPageLabel(returnTo), [returnTo]);

  // Get current URL without returnTo param (for serialization)
  const currentUrl = useMemo(() => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete('returnTo');

    const queryString = params.toString();
    return queryString ? `${pathname}?${queryString}` : pathname;
  }, [pathname, searchParams]);

  /**
   * Create a URL with returnTo param pointing to current location
   */
  const createReturnUrl = useCallback(
    (targetPath: string, additionalParams?: Record<string, string | undefined>): string => {
      // Build target URL params
      const params = new URLSearchParams();

      // Add additional params (filtering out undefined values)
      if (additionalParams) {
        Object.entries(additionalParams).forEach(([key, value]) => {
          if (value !== undefined && value !== null && value !== '') {
            params.set(key, value);
          }
        });
      }

      // Serialize current URL without any existing returnTo (prevents nesting)
      const currentWithoutReturnTo = new URLSearchParams(searchParams.toString());
      currentWithoutReturnTo.delete('returnTo');

      const currentQueryString = currentWithoutReturnTo.toString();
      const serializedCurrent = currentQueryString ? `${pathname}?${currentQueryString}` : pathname;

      // Add returnTo param
      params.set('returnTo', serializedCurrent);

      const queryString = params.toString();
      return queryString ? `${targetPath}?${queryString}` : targetPath;
    },
    [pathname, searchParams]
  );

  /**
   * Navigate back using returnTo or router.back()
   */
  const navigateBack = useCallback(() => {
    if (returnTo) {
      router.push(returnTo);
    } else if (fallbackToRouterBack) {
      router.back();
    }
  }, [returnTo, router, fallbackToRouterBack]);

  /**
   * Check if returnTo points to a specific page
   */
  const isReturningTo = useCallback(
    (pageName: string): boolean => {
      if (!returnTo) return false;

      try {
        const returnPath = returnTo.startsWith('/')
          ? returnTo.split('?')[0]
          : new URL(returnTo, 'http://localhost').pathname;

        // Ensure returnPath is defined
        if (!returnPath) return false;

        return returnPath === pageName || returnPath.startsWith(`${pageName}/`);
      } catch {
        return false;
      }
    },
    [returnTo]
  );

  return {
    returnTo,
    hasReturnTo,
    returnToLabel,
    currentUrl,
    createReturnUrl,
    navigateBack,
    isReturningTo,
  };
}
