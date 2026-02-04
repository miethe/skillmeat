'use client';

import { useRouter } from 'next/navigation';
import { UnifiedEntityModal, type ArtifactModalTab } from '@/components/entity/unified-entity-modal';
import type { Artifact } from '@/types/artifact';

/**
 * Props for CollectionArtifactModal
 */
interface CollectionArtifactModalProps {
  /** The artifact to display in the modal */
  artifact: Artifact | null;
  /** Whether the modal is open */
  open: boolean;
  /** Handler called when the modal should close */
  onClose: () => void;
  /** Initial tab to open when modal opens. Defaults to 'overview'. */
  initialTab?: ArtifactModalTab;
  /** Callback when tab changes. Useful for URL state synchronization. */
  onTabChange?: (tab: ArtifactModalTab) => void;
}

/**
 * Collection-specific wrapper for UnifiedEntityModal.
 *
 * This wrapper ensures navigation handlers are always provided when viewing
 * artifacts in collection pages. It encapsulates the common pattern of:
 * - Closing the modal before navigation
 * - Navigating to source pages in the marketplace
 * - Navigating to deployment pages in projects
 *
 * @example
 * ```tsx
 * <CollectionArtifactModal
 *   artifact={selectedArtifact}
 *   open={isDetailOpen}
 *   onClose={() => setIsDetailOpen(false)}
 *   initialTab="sync"
 *   onTabChange={(tab) => updateUrlTab(tab)}
 * />
 * ```
 */
export function CollectionArtifactModal({
  artifact,
  open,
  onClose,
  initialTab,
  onTabChange,
}: CollectionArtifactModalProps) {
  const router = useRouter();

  /**
   * Navigate to the artifact's source in the marketplace.
   * Closes the modal first to ensure clean navigation.
   */
  const handleNavigateToSource = (sourceId: string, artifactPath: string) => {
    onClose();
    router.push(`/marketplace/sources/${sourceId}?artifact=${encodeURIComponent(artifactPath)}`);
  };

  /**
   * Navigate to a deployment in a project.
   * Closes the modal first to ensure clean navigation.
   */
  const handleNavigateToDeployment = (projectPath: string, artifactId: string) => {
    onClose();
    const encodedPath = btoa(projectPath);
    router.push(`/projects/${encodedPath}/manage?artifact=${encodeURIComponent(artifactId)}`);
  };

  return (
    <UnifiedEntityModal
      artifact={artifact}
      open={open}
      onClose={onClose}
      onNavigateToSource={handleNavigateToSource}
      onNavigateToDeployment={handleNavigateToDeployment}
      initialTab={initialTab}
      onTabChange={onTabChange}
    />
  );
}

// Re-export ArtifactModalTab type for convenience
export type { ArtifactModalTab };
