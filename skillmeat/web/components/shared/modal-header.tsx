/**
 * Modal Header Component
 *
 * A reusable modal header wrapper that provides consistent styling for dialogs.
 * Includes optional icon, title, description, and actions slot.
 *
 * @example Basic usage
 * ```tsx
 * <ModalHeader title="Artifact Details" />
 * ```
 *
 * @example With icon and description
 * ```tsx
 * <ModalHeader
 *   icon={Package}
 *   title="Artifact Details"
 *   description="View and manage artifact configuration"
 * />
 * ```
 *
 * @example With actions
 * ```tsx
 * <ModalHeader
 *   icon={Package}
 *   iconClassName="text-primary"
 *   title="Artifact Details"
 *   actions={<Button variant="ghost" size="sm">Edit</Button>}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';

// ============================================================================
// Types
// ============================================================================

export interface ModalHeaderProps {
  /** Icon component to display before the title */
  icon?: React.ComponentType<{ className?: string }>;
  /** Additional CSS classes for the icon */
  iconClassName?: string;
  /** Modal title (required) */
  title: string;
  /** Optional description text below the title */
  description?: string;
  /** Optional actions slot for buttons on the right side */
  actions?: React.ReactNode;
  /** Additional CSS classes for the header container */
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

/**
 * ModalHeader - Consistent modal header layout
 *
 * Provides a standardized header structure with:
 * - Optional icon with customizable styling
 * - Title using DialogTitle for accessibility
 * - Optional description using DialogDescription
 * - Actions slot that floats right in the title row
 * - Border bottom styling for visual separation
 *
 * @param icon - Optional icon component
 * @param iconClassName - CSS classes for the icon
 * @param title - Modal title (required)
 * @param description - Optional description text
 * @param actions - Optional React node for action buttons
 * @param className - Additional CSS classes for the header
 */
export function ModalHeader({
  icon: Icon,
  iconClassName,
  title,
  description,
  actions,
  className,
}: ModalHeaderProps) {
  return (
    <DialogHeader className={cn('border-b px-6 pb-4 pt-6', className)}>
      <DialogTitle className="flex items-center gap-3">
        {Icon && <Icon className={cn('h-5 w-5 flex-shrink-0', iconClassName)} aria-hidden="true" />}
        <span className="flex-1 truncate">{title}</span>
        {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
      </DialogTitle>
      {description && <DialogDescription className="mt-1.5 pl-8">{description}</DialogDescription>}
    </DialogHeader>
  );
}
