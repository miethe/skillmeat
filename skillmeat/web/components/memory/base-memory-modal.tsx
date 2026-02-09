/**
 * Base Memory Modal Component
 *
 * A composition-based modal foundation for memory item dialogs.
 * Mirrors the structure of BaseArtifactModal but typed for MemoryItemResponse
 * instead of Artifact. Resolves icons from MEMORY_TYPE_CONFIG and uses a
 * truncated content preview as the title.
 *
 * Consumers provide tab definitions and children for tab content,
 * keeping all domain-specific logic in the parent component.
 *
 * @example Basic usage
 * ```tsx
 * <BaseMemoryModal
 *   memory={memory}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   activeTab={activeTab}
 *   onTabChange={setActiveTab}
 *   tabs={[
 *     { value: 'overview', label: 'Overview', icon: Info },
 *     { value: 'provenance', label: 'Provenance', icon: GitCommit },
 *   ]}
 *   headerActions={<MemoryTypeBadge type={memory.type} />}
 * >
 *   <TabContentWrapper value="overview">
 *     <p>Overview content</p>
 *   </TabContentWrapper>
 *   <TabContentWrapper value="provenance">
 *     <p>Provenance content</p>
 *   </TabContentWrapper>
 * </BaseMemoryModal>
 * ```
 */

'use client';

import * as React from 'react';
import { AlertCircle } from 'lucide-react';
import { Dialog, DialogContent } from '@/components/ui/dialog';
import { Tabs } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

import { ModalHeader } from '@/components/shared/modal-header';
import { TabNavigation, type Tab } from '@/components/shared/tab-navigation';

import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MEMORY_TYPE_CONFIG } from './memory-type-badge';

// ============================================================================
// Types
// ============================================================================

export interface BaseMemoryModalProps {
  /** The memory item to display in the modal */
  memory: MemoryItemResponse;
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
  /** Optional persistent footer rendered after the Tabs block inside DialogContent */
  footer?: React.ReactNode;
}

// ============================================================================
// Component
// ============================================================================

/**
 * BaseMemoryModal - Composition-based modal foundation for memory dialogs
 *
 * Provides:
 * - Dialog + DialogContent with standard 90vh sizing
 * - Memory type icon resolution from MEMORY_TYPE_CONFIG
 * - ModalHeader with truncated content preview as title
 * - TabNavigation with underline-styled tabs
 * - Children slot for tab content (TabContentWrapper / TabsContent)
 * - Optional persistent footer slot (rendered after tabs, inside DialogContent)
 *
 * Does NOT provide:
 * - Tab content implementations (passed as children)
 * - State management (activeTab is controlled externally)
 * - Queries, mutations, or business logic
 *
 * @param memory - The memory item to display
 * @param open - Dialog open state
 * @param onClose - Close handler
 * @param activeTab - Controlled active tab value
 * @param onTabChange - Tab change callback
 * @param tabs - Tab definitions for the navigation bar
 * @param headerActions - Optional actions rendered in the header
 * @param children - Tab content elements
 * @param className - Optional extra DialogContent classes
 * @param maxWidth - Optional max-width override
 * @param footer - Optional persistent footer below tabs
 */
export function BaseMemoryModal({
  memory,
  open,
  onClose,
  activeTab,
  onTabChange,
  tabs,
  headerActions,
  children,
  className,
  maxWidth,
  footer,
}: BaseMemoryModalProps) {
  // Resolve memory type icon from MEMORY_TYPE_CONFIG
  const config = MEMORY_TYPE_CONFIG[memory.type];
  const IconComponent = config?.icon ?? AlertCircle;
  const iconColor = config?.textClass ?? 'text-muted-foreground';

  // Title: truncated content preview (first ~60 chars)
  const title =
    memory.content.length > 60
      ? memory.content.slice(0, 60) + '...'
      : memory.content;

  // Fallback for unknown memory type (still render, just with alert icon)
  if (!config) {
    return (
      <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
        <DialogContent className="max-w-md">
          <ModalHeader
            icon={AlertCircle}
            iconClassName="text-yellow-500"
            title={title}
            description={`Memory type "${memory.type}" is not recognized.`}
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
          iconClassName={iconColor}
          title={title}
          actions={headerActions}
        />

        {/* Tabs */}
        <Tabs
          value={activeTab}
          onValueChange={onTabChange}
          className="flex min-h-0 flex-1 flex-col px-6"
        >
          <TabNavigation tabs={tabs} />

          {/* Tab content provided by consumer */}
          {children}
        </Tabs>

        {/* Persistent footer (outside Tabs, inside DialogContent) */}
        {footer}
      </DialogContent>
    </Dialog>
  );
}
