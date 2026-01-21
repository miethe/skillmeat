/**
 * Example usage of ConfidenceFilter component
 *
 * This file demonstrates how to integrate ConfidenceFilter
 * into a marketplace or artifact listing page.
 */

'use client';

import { useState } from 'react';
import { ConfidenceFilter } from './ConfidenceFilter';

export function ConfidenceFilterExample() {
  const [minConfidence, setMinConfidence] = useState(50);
  const [maxConfidence, setMaxConfidence] = useState(100);
  const [includeBelowThreshold, setIncludeBelowThreshold] = useState(false);

  return (
    <div className="rounded-lg border p-4">
      <h3 className="mb-4 text-lg font-semibold">Filter by Confidence</h3>

      <ConfidenceFilter
        minConfidence={minConfidence}
        maxConfidence={maxConfidence}
        includeBelowThreshold={includeBelowThreshold}
        onMinChange={setMinConfidence}
        onMaxChange={setMaxConfidence}
        onIncludeBelowThresholdChange={setIncludeBelowThreshold}
      />

      {/* Example: Show current filter state */}
      <div className="mt-4 rounded bg-muted p-3 text-sm">
        <p className="font-medium">Current Filter State:</p>
        <ul className="mt-2 space-y-1 text-muted-foreground">
          <li>Min Confidence: {minConfidence}%</li>
          <li>Max Confidence: {maxConfidence}%</li>
          <li>Include Below Threshold: {includeBelowThreshold ? 'Yes' : 'No'}</li>
        </ul>
      </div>
    </div>
  );
}

/**
 * Integration example with marketplace filters
 *
 * Add to your filter bar alongside type/status filters:
 *
 * ```tsx
 * // In marketplace/sources/[id]/page.tsx or similar
 *
 * const [filters, setFilters] = useState({
 *   artifact_type?: ArtifactType;
 *   status?: string;
 *   minConfidence: 50;
 *   maxConfidence: 100;
 *   includeBelowThreshold: false;
 * });
 *
 * // In your filters bar:
 * <div className="flex flex-wrap items-center gap-2">
 *   <ConfidenceFilter
 *     minConfidence={filters.minConfidence}
 *     maxConfidence={filters.maxConfidence}
 *     includeBelowThreshold={filters.includeBelowThreshold}
 *     onMinChange={(v) => setFilters(prev => ({ ...prev, minConfidence: v }))}
 *     onMaxChange={(v) => setFilters(prev => ({ ...prev, maxConfidence: v }))}
 *     onIncludeBelowThresholdChange={(v) =>
 *       setFilters(prev => ({ ...prev, includeBelowThreshold: v }))
 *     }
 *   />
 * </div>
 * ```
 *
 * Apply filters to your data:
 *
 * ```tsx
 * const filteredArtifacts = artifacts.filter(artifact => {
 *   // Type filter
 *   if (filters.artifact_type && artifact.artifact_type !== filters.artifact_type) {
 *     return false;
 *   }
 *
 *   // Confidence filter
 *   const score = artifact.confidence_score ?? 0;
 *
 *   // If below threshold and not including them, exclude
 *   if (score < 30 && !filters.includeBelowThreshold) {
 *     return false;
 *   }
 *
 *   // Otherwise check range
 *   if (score < filters.minConfidence || score > filters.maxConfidence) {
 *     return false;
 *   }
 *
 *   return true;
 * });
 * ```
 */
