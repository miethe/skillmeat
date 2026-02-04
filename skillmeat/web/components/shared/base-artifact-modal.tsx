/**
 * Base Artifact Modal Component
 *
 * A composition-based modal foundation for artifact-focused dialogs.
 * Encapsulates the common structure shared by ArtifactOperationsModal and
 * UnifiedEntityModal: Dialog wrapper, artifact header with icon resolution,
 * tab bar navigation, and scrollable content area.
 *
 * Consumers provide tab definitions and children for tab content,
 * keeping all domain-specific logic in the parent component.
 *
 * @example Basic usage
 * ```tsx
 * <BaseArtifactModal
 *   artifact={artifact}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   activeTab={activeTab}
 *   onTabChange={setActiveTab}
 *   tabs={[
 *     { value: 'overview', label: 'Overview', icon: Info },
 *     { value: 'settings', label: 'Settings', icon: Settings },
 *   ]}
 *   headerActions={<Button size="sm">Action</Button>}
 * >
 *   <TabContentWrapper value="overview">
 *     <p>Overview content</p>
 *   </TabContentWrapper>
 *   <TabContentWrapper value="settings">
 *     <p>Settings content</p>
 *   </TabContentWrapper>
 * </BaseArtifactModal>
 * ```
 *
 * @example With return navigation
 * ```tsx
 * <BaseArtifactModal
 *   artifact={artifact}
 *   open={isOpen}
 *   onClose={handleClose}
 *   activeTab={activeTab}
 *   onTabChange={setActiveTab}
 *   tabs={tabs}
 *   returnTo="/collection"
 *   onReturn={handleReturn}
 *   headerActions={<SyncButton />}
 * >
 *   {tabContent}
 * </BaseArtifactModal>
 * ```
 */

'use client';

import * as React from 'react';
import * as LucideIcons from 'lucide-react';
import { ArrowLeft, AlertCircle, FileText } from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Tabs } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

import { ModalHeader } from '@/components/shared/modal-header';
import { TabNavigation, type Tab } from '@/components/shared/tab-navigation';

import type { Artifact } from '@/types/artifact';
import { ARTIFACT_TYPES } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export interface BaseArtifactModalProps {
  /** The artifact to display in the modal */
  artifact: Artifact;
  /** Whether the modal is open */
  open: boolean;
  /** Handler for closing the modal */
  onClose: () => void;
  /** Current active tab (controlled) */
  activeTab: string;
  /** Tab change handler */
  onTabChange: (tab: string) => void;
  /** Tab definitions array */
  tabs: Tab[];
  /** Optional header action buttons (right side of header) */
  headerActions?: React.ReactNode;
  /** Tab content area (should contain TabContentWrapper or TabsContent elements) */
  children: React.ReactNode;
  /** Optional extra CSS classes for DialogContent */
  className?: string;
  /** Optional max-width override (default: 'max-w-5xl lg:max-w-6xl') */
  maxWidth?: string;
  /** URL to return to if navigated from another page */
  returnTo?: string;
  /** Handler for return navigation (called when return button is clicked) */
  onReturn?: () => void;
  /** Content to render between header and tabs (e.g., return button, alerts) */
  aboveTabsContent?: React.ReactNode;
}

// ============================================================================
// Component
// ============================================================================

/**
 * BaseArtifactModal - Composition-based modal foundation for artifact dialogs
 *
 * Provides:
 * - Dialog + DialogContent with standard 90vh sizing
 * - Artifact icon resolution from ARTIFACT_TYPES config
 * - ModalHeader with artifact name, description, icon, and actions slot
 * - Optional return-to-previous navigation bar
 * - TabNavigation with underline-styled tabs
 * - Children slot for tab content (TabContentWrapper / TabsContent)
 *
 * Does NOT provide:
 * - Tab content implementations (passed as children)
 * - State management (activeTab is controlled externally)
 * - Queries, mutations, or business logic
 *
 * @param artifact - The artifact to display
 * @param open - Dialog open state
 * @param onClose - Close handler
 * @param activeTab - Controlled active tab value
 * @param onTabChange - Tab change callback
 * @param tabs - Tab definitions for the navigation bar
 * @param headerActions - Optional actions rendered in the header
 * @param children - Tab content elements
 * @param className - Optional extra DialogContent classes
 * @param maxWidth - Optional max-width override
 * @param returnTo - Optional URL for return navigation
 * @param onReturn - Optional handler for return button click
 * @param aboveTabsContent - Optional content between header and tabs
 */
export function BaseArtifactModal({
  artifact,
  open,
  onClose,
  activeTab,
  onTabChange,
  tabs,
  headerActions,
  children,
  className,
  maxWidth,
  returnTo,
  onReturn,
  aboveTabsContent,
}: BaseArtifactModalProps) {
  // Resolve artifact icon from ARTIFACT_TYPES config
  const config = ARTIFACT_TYPES[artifact.type];
  const iconName = config?.icon ?? 'FileText';
  const IconLookup = (LucideIcons as Record<string, unknown>)[iconName] as
    | React.ComponentType<{ className?: string }>
    | undefined;
  const IconComponent = IconLookup || FileText;

  // Fallback for unknown artifact type
  if (!config) {
    return (
      <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <DialogContent className="max-w-md">
          <ModalHeader
            icon={AlertCircle}
            iconClassName="text-yellow-500"
            title={artifact.name}
            description={`Artifact type "${artifact.type}" is not supported.`}
          />
          <div className="flex justify-end p-4">
            <Button variant="outline" onClick={onClose}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent
        className={cn(
          'flex h-[90vh] max-h-[90vh] min-h-0 flex-col overflow-hidden p-0',
          maxWidth || 'max-w-5xl lg:max-w-6xl',
          className
        )}
      >
        {/* Header */}
        <ModalHeader
          icon={IconComponent}
          iconClassName={config.color}
          title={artifact.name}
          description={artifact.description}
          actions={headerActions}
        />

        {/* Return navigation */}
        {returnTo && onReturn && (
          <div className="border-b px-6 py-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={onReturn}
              className="gap-2 text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Return to previous page
            </Button>
          </div>
        )}

        {/* Optional content above tabs */}
        {aboveTabsContent}

        {/* Tabs */}
        <Tabs
          value={activeTab}
          onValueChange={onTabChange}
          className="flex h-full min-h-0 flex-1 flex-col px-6"
        >
          <TabNavigation tabs={tabs} />

          {/* Tab content provided by consumer */}
          {children}
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
