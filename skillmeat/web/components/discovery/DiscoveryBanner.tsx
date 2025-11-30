/**
 * Discovery Banner Component
 *
 * A banner that appears at the top of the /manage page when artifacts are discovered.
 * Prompts users to review and import existing artifacts from their collection.
 *
 * Features:
 * - Conditional rendering (only shows when artifacts are discovered)
 * - Dismissible with both button and close icon
 * - Accessible with proper ARIA attributes
 * - Correct plural handling for artifact count
 * - Uses shadcn/ui Alert components
 *
 * @example
 * ```tsx
 * <DiscoveryBanner
 *   discoveredCount={5}
 *   onReview={() => router.push('/import')}
 *   dismissible={true}
 * />
 * ```
 */

'use client';

import { useState, useEffect } from 'react';
import { Info, X } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useTrackDiscovery } from '@/lib/analytics';

export interface DiscoveryBannerProps {
  /** Number of artifacts discovered */
  discoveredCount: number;
  /** Callback when user clicks Review & Import */
  onReview: () => void;
  /** Whether the banner can be dismissed */
  dismissible?: boolean;
}

export function DiscoveryBanner({
  discoveredCount,
  onReview,
  dismissible = true,
}: DiscoveryBannerProps) {
  const [dismissed, setDismissed] = useState(false);
  const tracking = useTrackDiscovery();

  // Track banner view when it appears
  useEffect(() => {
    if (discoveredCount > 0 && !dismissed) {
      tracking.trackBannerView(discoveredCount);
    }
  }, [discoveredCount, dismissed, tracking]);

  if (dismissed || discoveredCount === 0) {
    return null;
  }

  const artifactText = discoveredCount === 1 ? 'Artifact' : 'Artifacts';

  return (
    <Alert className="mb-4 relative" role="status" aria-live="polite">
      <Info className="h-4 w-4" aria-hidden="true" />
      <AlertTitle>
        Found {discoveredCount} {artifactText}
      </AlertTitle>
      <AlertDescription>
        We discovered existing artifacts in your collection that can be imported.
        Review and import them to get started quickly.
      </AlertDescription>
      <div className="mt-3 flex gap-2">
        <Button size="sm" onClick={onReview}>
          Review & Import
        </Button>
        {dismissible && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setDismissed(true)}
            aria-label="Dismiss notification"
          >
            Dismiss
          </Button>
        )}
      </div>
      {dismissible && (
        <Button
          size="icon"
          variant="ghost"
          className="absolute top-2 right-2 h-6 w-6"
          onClick={() => setDismissed(true)}
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </Button>
      )}
    </Alert>
  );
}
