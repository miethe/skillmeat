'use client';

import * as React from 'react';
import { Plus } from 'lucide-react';

import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface StageConnectorProps {
  /** Called when the user clicks the "+" insert button (sequential only). */
  onAddStage?: () => void;
  /** Whether to render the hover-reveal "+" insert button. Defaults to true. */
  showAddButton?: boolean;
  /**
   * sequential — vertical line with optional hover "+" button.
   * parallel   — split/merge dashed visual (display-only, no add button).
   */
  variant?: 'sequential' | 'parallel';
  /** Additional CSS classes on the root element. */
  className?: string;
}

// ============================================================================
// Sequential connector
// ============================================================================

function SequentialConnector({
  onAddStage,
  showAddButton,
}: Pick<StageConnectorProps, 'onAddStage' | 'showAddButton'>) {
  const [hovered, setHovered] = React.useState(false);

  const showInsert = showAddButton && onAddStage;

  return (
    <div
      className="relative flex items-center justify-center py-1 group/connector"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      // Ensure the hover area is tall enough to be comfortable
      style={{ minHeight: '40px' }}
    >
      {/* Vertical line */}
      <div
        className={cn(
          'w-px transition-colors duration-150',
          // When hovering with an add button available, dim the line so the
          // "+" button reads clearly against it.
          hovered && showInsert
            ? 'bg-border/40'
            : 'bg-border',
        )}
        style={{ height: '32px' }}
        aria-hidden="true"
      />

      {/* Insert "+" button — fades in on connector hover */}
      {showInsert && (
        <button
          type="button"
          aria-label="Add stage between"
          onClick={onAddStage}
          className={cn(
            // Positioning: centred over the line
            'absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2',
            // Sizing: 24px circle
            'h-6 w-6 rounded-full',
            // Appearance
            'flex items-center justify-center',
            'border border-border bg-background',
            'text-muted-foreground',
            // Hover state on the button itself
            'hover:border-primary hover:text-primary hover:bg-primary/5',
            // Focus ring
            'focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1',
            // Fade animation driven by parent hover
            'transition-all duration-150',
            hovered ? 'opacity-100 scale-100' : 'opacity-0 scale-75 pointer-events-none',
          )}
        >
          <Plus className="h-3 w-3" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Parallel connector
// ============================================================================

/**
 * Parallel connector — split/merge visual.
 *
 * Renders a top stem → horizontal bar with two downward legs → bottom stem,
 * all in dashed muted lines. Display-only; no interactive elements.
 *
 * ASCII reference from spec:
 *
 *         |
 *     +---+---+
 *     |       |
 *  [Stage]  [Stage]
 *     |       |
 *     +---+---+
 *         |
 */
function ParallelConnector() {
  return (
    <div
      aria-hidden="true"
      className="flex flex-col items-center py-1 text-muted-foreground"
    >
      {/* Top stem */}
      <div className="w-px border-l border-dashed border-muted-foreground/40" style={{ height: '12px' }} />

      {/* Diverge bar + two legs */}
      <div className="relative flex items-start justify-center w-16">
        {/* Horizontal bar */}
        <div
          className="absolute top-0 left-0 right-0 border-t border-dashed border-muted-foreground/40"
          style={{ top: 0 }}
        />
        {/* Left leg */}
        <div
          className="border-l border-dashed border-muted-foreground/40"
          style={{ height: '20px', marginLeft: '0px' }}
        />
        {/* Right leg */}
        <div
          className="border-r border-dashed border-muted-foreground/40 absolute right-0"
          style={{ height: '20px' }}
        />
      </div>

      {/* Converge bar + two legs */}
      <div className="relative flex items-end justify-center w-16">
        {/* Left leg */}
        <div
          className="border-l border-dashed border-muted-foreground/40"
          style={{ height: '20px' }}
        />
        {/* Right leg */}
        <div
          className="border-r border-dashed border-muted-foreground/40 absolute right-0"
          style={{ height: '20px' }}
        />
        {/* Horizontal bar */}
        <div
          className="absolute bottom-0 left-0 right-0 border-b border-dashed border-muted-foreground/40"
        />
      </div>

      {/* Bottom stem */}
      <div className="w-px border-l border-dashed border-muted-foreground/40" style={{ height: '12px' }} />
    </div>
  );
}

// ============================================================================
// StageConnector (public API)
// ============================================================================

/**
 * StageConnector — the visual bridge placed between two StageCard elements in
 * the workflow builder canvas.
 *
 * Sequential variant:
 *   - 2px vertical line (border colour) centred between cards.
 *   - On hover: a small 24px "+" circle fades in at the midpoint, letting the
 *     user insert a new stage between existing ones.
 *
 * Parallel variant (display-only in v1):
 *   - Dashed split/merge visual to signal that two stages run in parallel.
 *   - No interactive elements.
 *
 * @example
 * // Between two sequential stages (with insert)
 * <StageConnector onAddStage={() => insertStage(index)} />
 *
 * // Between two parallel stages (purely visual)
 * <StageConnector variant="parallel" showAddButton={false} />
 */
export function StageConnector({
  onAddStage,
  showAddButton = true,
  variant = 'sequential',
  className,
}: StageConnectorProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-center select-none',
        className,
      )}
    >
      {variant === 'sequential' ? (
        <SequentialConnector onAddStage={onAddStage} showAddButton={showAddButton} />
      ) : (
        <ParallelConnector />
      )}
    </div>
  );
}
