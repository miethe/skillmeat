'use client';

/**
 * ConsolidationClusterDetail
 *
 * Minimal stub — full implementation is in a separate task.
 * Renders a placeholder for the cluster detail panel.
 */

import type { ConsolidationCluster } from '@/types/similarity';

interface ConsolidationClusterDetailProps {
  cluster: ConsolidationCluster;
  onClose: () => void;
}

export function ConsolidationClusterDetail({ cluster, onClose }: ConsolidationClusterDetailProps) {
  return (
    <div
      className="rounded-lg border border-dashed p-8 text-center text-muted-foreground"
      role="region"
      aria-label={`Cluster detail for cluster ${cluster.cluster_id}`}
    >
      <p className="text-sm">Cluster detail view coming soon.</p>
      <button
        onClick={onClose}
        className="mt-4 text-xs underline hover:no-underline"
        aria-label="Close cluster detail"
      >
        Close
      </button>
    </div>
  );
}
