/**
 * Discovery Components Module
 *
 * Provides UI components for artifact discovery and import workflows.
 *
 * Components:
 * - DiscoveryBanner: Alert banner for discovered artifacts
 * - BulkImportModal: Modal for reviewing and importing discovered artifacts
 * - AutoPopulationForm: Form that auto-populates artifact metadata from GitHub
 * - ParameterEditorModal: Modal for editing artifact parameters
 *
 * @example
 * ```tsx
 * import { DiscoveryBanner, BulkImportModal, AutoPopulationForm } from '@/components/discovery';
 *
 * export function ManagePage() {
 *   const [modalOpen, setModalOpen] = useState(false);
 *   const [artifacts, setArtifacts] = useState<DiscoveredArtifact[]>([]);
 *
 *   return (
 *     <div>
 *       <DiscoveryBanner
 *         discoveredCount={5}
 *         onReview={() => setModalOpen(true)}
 *       />
 *       <BulkImportModal
 *         artifacts={artifacts}
 *         open={modalOpen}
 *         onClose={() => setModalOpen(false)}
 *         onImport={async (selected) => {
 *           // Handle import
 *         }}
 *       />
 *       <AutoPopulationForm
 *         artifactType="skill"
 *         onImport={handleImport}
 *       />
 *     </div>
 *   );
 * }
 * ```
 */

export { DiscoveryBanner } from './DiscoveryBanner';
export type { DiscoveryBannerProps } from './DiscoveryBanner';

export { BulkImportModal } from './BulkImportModal';
export type { BulkImportModalProps, DiscoveredArtifact } from './BulkImportModal';

export { AutoPopulationForm } from './AutoPopulationForm';
export type { AutoPopulationFormProps } from './AutoPopulationForm';

export { ParameterEditorModal } from './ParameterEditorModal';
export type { ParameterEditorModalProps, ArtifactParameters } from './ParameterEditorModal';

export { DiscoveryTab } from './DiscoveryTab';
export type { DiscoveryTabProps } from './DiscoveryTab';

export { ArtifactActions } from './ArtifactActions';
export type { ArtifactActionsProps } from './ArtifactActions';

export { SkipPreferencesList } from './SkipPreferencesList';
export type { SkipPreferencesListProps } from './SkipPreferencesList';

export { DuplicateReviewModal } from './DuplicateReviewModal';
export type { DuplicateReviewModalProps } from './DuplicateReviewModal';

export { DuplicateReviewTab } from './DuplicateReviewTab';
export type { DuplicateReviewTabProps } from './DuplicateReviewTab';
