'use client';

import { useRouter } from 'next/navigation';
import { UnifiedEntityModal } from '@/components/entity/unified-entity-modal';
import type { Artifact } from '@/types/artifact';

/**
 * Props for ProjectArtifactModal component.
 *
 * This wrapper ensures navigation handlers are always provided to UnifiedEntityModal
 * when used in project page contexts.
 */
export interface ProjectArtifactModalProps {
  /** The artifact to display in the modal */
  artifact: Artifact | null;
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal is closed */
  onClose: () => void;
  /** Current project path to detect same-project navigation */
  currentProjectPath?: string;
}

/**
 * ProjectArtifactModal - A wrapper around UnifiedEntityModal for project pages.
 *
 * Ensures navigation handlers are always provided, preventing issues where pages
 * forget to pass them. Handles:
 * - Navigation to source in marketplace
 * - Navigation to deployment (same-project detection)
 *
 * @example
 * ```tsx
 * <ProjectArtifactModal
 *   artifact={selectedArtifact}
 *   open={isModalOpen}
 *   onClose={() => setIsModalOpen(false)}
 *   currentProjectPath={project.path}
 * />
 * ```
 */
export function ProjectArtifactModal({
  artifact,
  open,
  onClose,
  currentProjectPath,
}: ProjectArtifactModalProps) {
  const router = useRouter();

  /**
   * Navigate to the artifact's source in the marketplace.
   * Closes the modal before navigating.
   */
  const handleNavigateToSource = (sourceId: string, artifactPath: string) => {
    onClose();
    router.push(`/marketplace/sources/${sourceId}?artifact=${encodeURIComponent(artifactPath)}`);
  };

  /**
   * Navigate to the artifact's deployment in a project.
   * If the target project is the same as the current project, just close the modal.
   * Otherwise, navigate to the project's manage page.
   */
  const handleNavigateToDeployment = (projectPath: string, artifactId: string) => {
    onClose();

    // If same project as current, no need to navigate - modal close is sufficient
    if (currentProjectPath && projectPath === currentProjectPath) {
      return;
    }

    // Navigate to the target project's manage page with artifact highlighted
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
    />
  );
}
