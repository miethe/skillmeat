'use client';

/**
 * SlideOverPanel Component
 *
 * A reusable right-side slide-over panel that animates in from the right edge.
 * Composes from the Sheet primitive pattern but adds full animation, focus trap,
 * Escape key handling, and width variants as specified in the workflow-orchestration
 * UI spec (Section 3.2).
 *
 * @example Basic usage
 * ```tsx
 * <SlideOverPanel
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   title="Edit Stage"
 *   description="Configure stage settings and agent assignments"
 * >
 *   <StageEditorForm stage={stage} />
 * </SlideOverPanel>
 * ```
 *
 * @example With explicit width variant
 * ```tsx
 * <SlideOverPanel
 *   open={isOpen}
 *   onClose={handleClose}
 *   title="Workflow Settings"
 *   width="lg"
 * >
 *   {children}
 * </SlideOverPanel>
 * ```
 */

import * as React from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export type SlideOverPanelWidth = 'sm' | 'md' | 'lg' | 'xl';

export interface SlideOverPanelProps {
  /** Controls whether the panel is visible */
  open: boolean;
  /** Called when the panel should close (backdrop click, X button, or Escape key) */
  onClose: () => void;
  /** Panel heading — rendered as an h2 */
  title: string;
  /** Optional descriptive text rendered below the title in muted style */
  description?: string;
  /**
   * Panel width variant:
   * - sm: 320px
   * - md: 480px (default)
   * - lg: 640px
   * - xl: 800px
   */
  width?: SlideOverPanelWidth;
  /** Panel body content — rendered in a scrollable area below the header */
  children: React.ReactNode;
  /** Additional CSS classes for the panel container */
  className?: string;
}

// ============================================================================
// Constants
// ============================================================================

const WIDTH_CLASSES: Record<SlideOverPanelWidth, string> = {
  sm: 'w-[320px]',
  md: 'w-[480px]',
  lg: 'w-[640px]',
  xl: 'w-[800px]',
};

// Focusable element selectors for focus trap
const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

// ============================================================================
// Hook: useFocusTrap
// ============================================================================

/**
 * Traps keyboard focus within the given container element while active.
 * Returns focus to the previously-focused element on deactivation.
 */
function useFocusTrap(containerRef: React.RefObject<HTMLElement | null>, active: boolean) {
  // Store the element that had focus before the panel opened
  const previousFocusRef = React.useRef<HTMLElement | null>(null);

  React.useEffect(() => {
    if (!active) return;

    // Save current focus target so we can restore it on close
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Move focus into the panel (first focusable child, or the panel itself)
    const container = containerRef.current;
    if (container) {
      const firstFocusable = container.querySelector<HTMLElement>(FOCUSABLE_SELECTOR);
      if (firstFocusable) {
        firstFocusable.focus();
      } else {
        container.focus();
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Tab' || !container) return;

      const focusableElements = Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      ).filter((el) => !el.closest('[hidden]'));

      if (focusableElements.length === 0) return;

      const firstEl = focusableElements[0];
      const lastEl = focusableElements[focusableElements.length - 1];

      if (event.shiftKey) {
        // Shift+Tab: if we're at the first element, wrap to last
        if (document.activeElement === firstEl) {
          event.preventDefault();
          lastEl.focus();
        }
      } else {
        // Tab: if we're at the last element, wrap to first
        if (document.activeElement === lastEl) {
          event.preventDefault();
          firstEl.focus();
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      // Restore focus to the element that was focused before the panel opened
      previousFocusRef.current?.focus();
    };
  }, [active, containerRef]);
}

// ============================================================================
// Hook: useEscapeKey
// ============================================================================

function useEscapeKey(onEscape: () => void, active: boolean) {
  React.useEffect(() => {
    if (!active) return;

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        event.preventDefault();
        onEscape();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [active, onEscape]);
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * SlideOverPanel — right-edge slide-over panel with backdrop, focus trap,
 * Escape key handling, and animated enter/exit transitions.
 *
 * Animation spec (from workflow-orchestration-ui-spec.md §3.2 + animation table):
 * - Open:  translate-x-full → translate-x-0, 300ms ease-out
 * - Close: translate-x-0 → translate-x-full, 200ms ease-in
 */
export function SlideOverPanel({
  open,
  onClose,
  title,
  description,
  width = 'md',
  children,
  className,
}: SlideOverPanelProps) {
  const panelRef = React.useRef<HTMLDivElement>(null);

  // We mount the panel immediately but control visibility via CSS so that the
  // exit animation plays before the element is removed from the DOM.
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    if (open) {
      setMounted(true);
    }
    // Keep mounted during close animation; unmount after transition ends
    // The onTransitionEnd handler below handles the actual unmount.
  }, [open]);

  const handleTransitionEnd = React.useCallback(() => {
    if (!open) {
      setMounted(false);
    }
  }, [open]);

  // Focus trap — active only when panel is fully open
  useFocusTrap(panelRef, open);

  // Escape key — close on Escape, matching spec §3.2 keyboard table
  useEscapeKey(onClose, open);

  if (!mounted) return null;

  return (
    // Portal-style fixed overlay root
    <div
      className="fixed inset-0 z-50"
      // Prevent interaction with underlying content when open
      aria-hidden={!open}
    >
      {/* Backdrop — semi-transparent overlay, click to close */}
      <div
        className={cn(
          'fixed inset-0 bg-black/20 transition-opacity duration-300',
          open ? 'opacity-100' : 'opacity-0 pointer-events-none'
        )}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel — slides in from the right edge */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        onTransitionEnd={handleTransitionEnd}
        className={cn(
          // Position & dimensions
          'fixed inset-y-0 right-0 flex flex-col',
          'bg-background border-l shadow-xl',
          // Width variant
          WIDTH_CLASSES[width],
          // Slide animation — open: ease-out 300ms, close: ease-in 200ms
          'transition-transform',
          open
            ? 'translate-x-0 duration-300 ease-out'
            : 'translate-x-full duration-200 ease-in',
          className
        )}
      >
        {/* Header */}
        <div className="flex flex-shrink-0 items-start justify-between gap-4 border-b px-6 py-4">
          <div className="flex flex-col gap-1 min-w-0">
            <h2 className="text-lg font-semibold leading-tight text-foreground truncate">
              {title}
            </h2>
            {description && (
              <p className="text-sm text-muted-foreground leading-snug">{description}</p>
            )}
          </div>

          {/* Close button */}
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className={cn(
              'flex-shrink-0 rounded-sm p-1',
              'text-muted-foreground',
              'opacity-70 hover:opacity-100',
              'ring-offset-background transition-opacity',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
              'disabled:pointer-events-none'
            )}
          >
            <X className="h-4 w-4" aria-hidden="true" />
            <span className="sr-only">Close</span>
          </button>
        </div>

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto px-6 py-4">{children}</div>
      </div>
    </div>
  );
}
