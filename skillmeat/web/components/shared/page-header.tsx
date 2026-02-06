/**
 * PageHeader Component
 *
 * A reusable header component for pages with title, description, icon, and actions slot.
 * Responsive layout that stacks on mobile and expands horizontally on larger screens.
 *
 * @example Basic usage
 * ```tsx
 * <PageHeader
 *   title="Collections"
 *   description="Browse & Discover your artifact collection"
 * />
 * ```
 *
 * @example With icon and actions
 * ```tsx
 * <PageHeader
 *   title="Collections"
 *   description="Browse & Discover your artifact collection"
 *   icon={<Library className="h-6 w-6" />}
 *   actions={<Button variant="outline">Refresh</Button>}
 * />
 * ```
 */

import * as React from 'react';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface PageHeaderProps {
  /** Page title (rendered as h1) */
  title: string;
  /** Optional description text displayed below the title */
  description?: string;
  /** Optional icon displayed before the title */
  icon?: React.ReactNode;
  /** Optional actions slot (buttons, etc.) displayed on the right */
  actions?: React.ReactNode;
  /** Additional CSS classes for the container */
  className?: string;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * PageHeader - Consistent page header layout
 *
 * Provides a standardized header structure with:
 * - Semantic h1 heading for accessibility
 * - Optional icon alongside title
 * - Optional description with muted styling
 * - Actions slot that floats right on desktop, stacks on mobile
 *
 * @param title - Page title (required)
 * @param description - Optional description text
 * @param icon - Optional React node for icon
 * @param actions - Optional React node for action buttons
 * @param className - Additional CSS classes
 */
export function PageHeader({ title, description, icon, actions, className }: PageHeaderProps) {
  return (
    <header
      className={cn('flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between', className)}
    >
      {/* Title section with icon */}
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-3">
          {icon && (
            <span className="flex-shrink-0 text-muted-foreground" aria-hidden="true">
              {icon}
            </span>
          )}
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">{title}</h1>
        </div>
        {description && <p className="text-sm text-muted-foreground sm:text-base">{description}</p>}
      </div>

      {/* Actions slot */}
      {actions && <div className="flex flex-shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}
