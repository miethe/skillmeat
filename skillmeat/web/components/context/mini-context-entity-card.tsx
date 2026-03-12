/**
 * MiniContextEntityCard Component
 *
 * Compact context entity card for picker/grid layouts. Matches the visual
 * scale of MiniArtifactCard with a colored left bar, icon, name, type badge,
 * and description. Supports selected, disabled, and hover states.
 *
 * Layout:
 * +--+---------------------------+
 * |C |  [Icon] Entity Name       |
 * |O |  [TypeBadge]              |
 * |L |                           |
 * |O |  Description text that    |
 * |R |  can wrap up to two lines |
 * |B |  before clamping...       |
 * |A |                           |
 * |R |                           |
 * +--+---------------------------+
 */

'use client';

import * as React from 'react';
import { FileText, Settings, BookOpen, Shield, Clock, File, Check } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import {
  getEntityTypeConfig,
  type ContextEntityTypeConfig,
} from '@/lib/context-entity-config';
import type { ContextEntity } from '@/types/context-entity';

// ============================================================================
// Icon resolver (mirrors context-entity-card.tsx)
// ============================================================================

function resolveIcon(iconName: ContextEntityTypeConfig['icon']): React.ElementType {
  switch (iconName) {
    case 'settings':
      return Settings;
    case 'file-text':
      return FileText;
    case 'shield':
      return Shield;
    case 'book-open':
      return BookOpen;
    case 'clock':
      return Clock;
    case 'file':
    default:
      return File;
  }
}

// ============================================================================
// Types
// ============================================================================

export interface MiniContextEntityCardProps {
  /** The context entity to display */
  entity: ContextEntity;
  /** Click handler — not called when card is disabled */
  onClick?: () => void;
  /** When true, reduces opacity and blocks interaction */
  disabled?: boolean;
  /** When true, renders a checkmark overlay and ring highlight */
  selected?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// MiniContextEntityCard
// ============================================================================

/**
 * MiniContextEntityCard — Compact card for context entities in picker layouts.
 *
 * Follows MiniArtifactCard visual conventions: fixed-width colored left border,
 * icon + name row, type badge, and 2-line clamped description. Supports
 * selected (checkmark overlay) and disabled (reduced opacity, no hover) states.
 *
 * @example
 * ```tsx
 * <MiniContextEntityCard
 *   entity={entity}
 *   selected={selectedIds.has(entity.id)}
 *   onClick={() => toggleSelection(entity.id)}
 * />
 * ```
 */
export function MiniContextEntityCard({
  entity,
  onClick,
  disabled = false,
  selected = false,
  className,
}: MiniContextEntityCardProps) {
  const config = getEntityTypeConfig(entity.entity_type);
  const Icon = resolveIcon(config.icon);

  const handleClick = () => {
    if (!disabled) {
      onClick?.();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!disabled && (e.key === 'Enter' || e.key === ' ')) {
      e.preventDefault();
      onClick?.();
    }
  };

  return (
    <div
      className={cn(
        // Base layout — matches MiniArtifactCard dimensions and structure
        'relative flex w-full min-h-[100px] flex-col rounded-lg border border-l-[3px] bg-card p-3',
        'shadow-sm transition-all duration-150',
        // Left color bar from type config
        config.borderClass,
        // Hover — only when not disabled
        !disabled && 'cursor-pointer hover:shadow-md hover:bg-accent/30',
        // Focus ring
        !disabled && 'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
        // Selected state ring
        selected && 'ring-2 ring-primary ring-offset-1',
        // Disabled state
        disabled && 'cursor-not-allowed opacity-50',
        className
      )}
      role="option"
      aria-selected={selected}
      aria-disabled={disabled}
      tabIndex={disabled ? -1 : 0}
      aria-label={`${entity.name}, ${config.label} context entity${selected ? ', selected' : ''}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
    >
      {/* Selected checkmark overlay (top-right corner) */}
      {selected && (
        <span
          className="absolute right-2 top-2 flex h-4 w-4 items-center justify-center rounded-full bg-primary text-primary-foreground"
          aria-hidden="true"
        >
          <Check className="h-2.5 w-2.5" strokeWidth={3} />
        </span>
      )}

      {/* Icon + Name row */}
      <div className="flex items-center gap-1.5 pr-5">
        <Icon
          className={cn('h-4 w-4 flex-shrink-0', config.textClass)}
          aria-hidden="true"
        />
        <span
          className="truncate text-sm font-medium leading-tight"
          title={entity.name}
        >
          {entity.name}
        </span>
      </div>

      {/* Type badge */}
      <div className="mt-1">
        <Badge
          variant="outline"
          className={cn(
            'gap-1 rounded-full border-transparent px-1.5 py-0 text-[10px] font-medium',
            config.bgClass,
            config.textClass
          )}
        >
          {config.label}
        </Badge>
      </div>

      {/* Description — 2-line clamp */}
      <div className="mt-1.5">
        {entity.description ? (
          <p
            className="line-clamp-2 text-xs leading-[14px] text-muted-foreground"
            title={entity.description}
          >
            {entity.description}
          </p>
        ) : (
          <p className="text-xs italic text-muted-foreground/60">No description</p>
        )}
      </div>
    </div>
  );
}
