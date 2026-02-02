/**
 * Cross Navigation Buttons Component
 *
 * Provides navigation buttons for moving between collection and manage modals.
 * Preserves context through URL query parameters using the useReturnTo hook.
 *
 * Features:
 * - Serializes full URL state including filters, tags, and sort options
 * - Prevents nested returnTo parameters (only one level)
 * - Provides clear visual indication of navigation direction
 *
 * @example On collection page
 * ```tsx
 * <CrossNavigationButtons
 *   currentPage="collection"
 *   artifactId="skill:canvas-design"
 *   onNavigate={() => closeModal()}
 * />
 * // Renders: "Manage Artifact ->" button
 * ```
 *
 * @example On manage page
 * ```tsx
 * <CrossNavigationButtons
 *   currentPage="manage"
 *   artifactId="skill:canvas-design"
 *   collectionId="default"
 * />
 * // Renders: "<- Collection Details" button
 * ```
 */

'use client';

import * as React from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft, ArrowRight, Settings, Library } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useReturnTo } from '@/hooks';

// ============================================================================
// Types
// ============================================================================

export interface CrossNavigationButtonsProps {
  /** Which page the user is currently on */
  currentPage: 'collection' | 'manage';
  /** The artifact ID to pass in navigation */
  artifactId: string;
  /** Optional collection ID for navigation context */
  collectionId?: string;
  /** Additional CSS classes for the button container */
  className?: string;
  /** Callback before navigation (e.g., to close modal) */
  onNavigate?: () => void;
}

// ============================================================================
// Component
// ============================================================================

/**
 * CrossNavigationButtons - Navigate between collection and manage views
 *
 * Renders appropriate navigation button based on current page:
 * - On collection page: "Manage Artifact" button to go to manage page
 * - On manage page: "Collection Details" button to return to collection
 *
 * Uses the useReturnTo hook to properly serialize current URL state,
 * preserving filters, tags, and other query parameters.
 *
 * @param currentPage - Current page context ('collection' or 'manage')
 * @param artifactId - Artifact ID to include in navigation
 * @param collectionId - Optional collection ID for context
 * @param className - Additional CSS classes
 * @param onNavigate - Optional callback before navigation
 */
export function CrossNavigationButtons({
  currentPage,
  artifactId,
  collectionId,
  className,
  onNavigate,
}: CrossNavigationButtonsProps) {
  const router = useRouter();
  const { createReturnUrl } = useReturnTo();

  /**
   * Navigate to the manage page with artifact context.
   * Serializes current URL (with filters) as returnTo param.
   */
  const handleNavigateToManage = React.useCallback(() => {
    onNavigate?.();

    // Build URL with returnTo pointing to current page (with all filters)
    const url = createReturnUrl('/manage', {
      artifact: artifactId,
      collection: collectionId,
    });

    router.push(url);
  }, [router, createReturnUrl, artifactId, collectionId, onNavigate]);

  /**
   * Navigate to the collection page with artifact context.
   * Serializes current URL (with filters) as returnTo param.
   */
  const handleNavigateToCollection = React.useCallback(() => {
    onNavigate?.();

    // Build URL with returnTo pointing to current page (with all filters)
    const url = createReturnUrl('/collection', {
      artifact: artifactId,
      collection: collectionId,
    });

    router.push(url);
  }, [router, createReturnUrl, artifactId, collectionId, onNavigate]);

  if (currentPage === 'collection') {
    return (
      <div className={cn('flex items-center', className)}>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleNavigateToManage}
          className="gap-2 text-muted-foreground hover:text-foreground"
          aria-label="Navigate to manage artifact page"
        >
          <Settings className="h-4 w-4" aria-hidden="true" />
          <span>Manage Artifact</span>
          <ArrowRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    );
  }

  // currentPage === 'manage'
  return (
    <div className={cn('flex items-center', className)}>
      <Button
        variant="ghost"
        size="sm"
        onClick={handleNavigateToCollection}
        className="gap-2 text-muted-foreground hover:text-foreground"
        aria-label="Navigate to collection details page"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        <Library className="h-4 w-4" aria-hidden="true" />
        <span>Collection Details</span>
      </Button>
    </div>
  );
}
