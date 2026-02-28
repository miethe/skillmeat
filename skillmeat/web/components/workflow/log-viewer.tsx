'use client';

/**
 * LogViewer — monospace log display panel for stage execution output.
 *
 * Features:
 *   - Dark terminal-style background with monospace font
 *   - Optional timestamp prefix per line (muted/dim color)
 *   - Optional line numbers (non-selectable, right-aligned, muted)
 *   - Auto-scroll to bottom when new lines arrive (streaming mode)
 *   - "Scroll to bottom" floating button when user scrolls up
 *   - Error lines ([ERROR], [FATAL], level:'error') highlighted red
 *   - Warning lines ([WARN], level:'warn') highlighted amber
 *   - Debug lines (level:'debug') shown in muted color
 *   - Empty state: "Waiting for logs..." with subtle pulse animation
 *   - Max-height container with internal scroll (not page scroll)
 *
 * Accessibility:
 *   - role="log" on the container
 *   - aria-live="polite" for screen reader announcements
 *   - aria-label="Stage execution logs"
 *   - Scroll button has aria-label="Scroll to bottom"
 */

import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface LogLine {
  /** Optional ISO 8601 or HH:MM:SS timestamp shown as a dim prefix. */
  timestamp?: string;
  /** The log message text. May contain inline [ERROR]/[WARN]/[FATAL] tokens. */
  message: string;
  /** Explicit severity level — takes precedence over message token detection. */
  level?: 'info' | 'warn' | 'error' | 'debug';
}

export interface LogViewerProps {
  /** Log lines to display. Append new lines for streaming. */
  lines: LogLine[];
  /**
   * When true, auto-scroll is active by default.
   * The component will track new lines and scroll to the bottom
   * unless the user has manually scrolled up.
   */
  isStreaming?: boolean;
  /** CSS max-height value for the scrollable viewport. Default: "24rem" (h-96). */
  maxHeight?: string;
  /** Render line numbers in the left gutter. Default: true. */
  showLineNumbers?: boolean;
  /** Additional Tailwind class overrides for the root wrapper. */
  className?: string;
}

// ============================================================================
// Helpers
// ============================================================================

/** Threshold in px from the bottom — within this distance we consider the
 *  viewport "at the bottom" and keep auto-scroll active. */
const AT_BOTTOM_THRESHOLD = 60;

/**
 * Detect severity from the message text when no explicit `level` is provided.
 * Returns 'error' for [ERROR]/[FATAL], 'warn' for [WARN], otherwise undefined.
 */
function detectLevelFromMessage(
  message: string
): 'error' | 'warn' | undefined {
  const upper = message.toUpperCase();
  if (/\[(ERROR|FATAL)\]/.test(upper)) return 'error';
  if (/\[WARN\]/.test(upper)) return 'warn';
  return undefined;
}

/**
 * Resolve the effective severity level for a line.
 * Explicit `level` prop takes precedence; falls back to message-token detection.
 */
function resolveLevel(
  line: LogLine
): 'info' | 'warn' | 'error' | 'debug' | undefined {
  if (line.level) return line.level;
  return detectLevelFromMessage(line.message);
}

// ============================================================================
// Sub-components
// ============================================================================

// --------------------------------------------------------------------------
// Empty state
// --------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="flex h-full min-h-[4rem] items-center justify-center px-3 py-4">
      <span
        className={cn(
          'font-mono text-xs italic text-muted-foreground/50',
          'animate-pulse'
        )}
      >
        Waiting for logs...
      </span>
    </div>
  );
}

// --------------------------------------------------------------------------
// Single log line
// --------------------------------------------------------------------------

interface LogLineRowProps {
  line: LogLine;
  lineNumber: number;
  showLineNumbers: boolean;
}

function LogLineRow({ line, lineNumber, showLineNumbers }: LogLineRowProps) {
  const level = resolveLevel(line);

  const rowClass = cn(
    'flex min-w-0 items-baseline gap-2 rounded-sm px-2 py-px leading-relaxed',
    level === 'error' && 'bg-red-500/10 text-red-400 dark:text-red-400',
    level === 'warn' && 'text-amber-500 dark:text-amber-400',
    level === 'debug' && 'text-muted-foreground/60',
    (!level || level === 'info') && 'text-foreground/90'
  );

  return (
    <div className={rowClass}>
      {/* Line number gutter */}
      {showLineNumbers && (
        <span
          className={cn(
            'shrink-0 select-none text-right font-mono text-[10px]',
            'w-7 text-muted-foreground/30',
            level === 'error' && 'text-red-400/40',
            level === 'warn' && 'text-amber-500/40'
          )}
          aria-hidden="true"
        >
          {lineNumber}
        </span>
      )}

      {/* Timestamp */}
      {line.timestamp && (
        <span
          className={cn(
            'shrink-0 select-none font-mono text-[10px]',
            level === 'error'
              ? 'text-red-400/60'
              : level === 'warn'
              ? 'text-amber-500/60'
              : 'text-muted-foreground/40'
          )}
        >
          [{line.timestamp}]
        </span>
      )}

      {/* Message */}
      <span className="min-w-0 break-all font-mono text-xs">
        {line.message}
      </span>
    </div>
  );
}

// ============================================================================
// LogViewer — main component
// ============================================================================

/**
 * LogViewer renders a scrollable, monospace log output panel.
 *
 * Pass `isStreaming` to enable auto-scroll behavior. The component tracks
 * whether the user has manually scrolled up and disables auto-scroll until
 * the "Scroll to bottom" button is pressed.
 */
export function LogViewer({
  lines,
  isStreaming = false,
  maxHeight = '24rem',
  showLineNumbers = true,
  className,
}: LogViewerProps) {
  const viewportRef = React.useRef<HTMLDivElement>(null);

  /**
   * Whether auto-scroll is currently active.
   * Starts active when isStreaming=true; disabled when the user manually
   * scrolls up; re-enabled when the "scroll to bottom" button is pressed.
   */
  const [autoScroll, setAutoScroll] = React.useState(isStreaming);

  /**
   * Whether to show the "Scroll to bottom" button.
   * Shown whenever the user has scrolled up enough to no longer see the end.
   */
  const [showScrollBtn, setShowScrollBtn] = React.useState(false);

  // Sync autoScroll state when isStreaming prop changes
  React.useEffect(() => {
    if (isStreaming) {
      setAutoScroll(true);
    }
  }, [isStreaming]);

  // -------------------------------------------------------------------------
  // Scroll detection
  // -------------------------------------------------------------------------

  const handleScroll = React.useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;

    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    const isAtBottom = distanceFromBottom <= AT_BOTTOM_THRESHOLD;

    // If user scrolled up, disable auto-scroll and reveal the button
    if (!isAtBottom && autoScroll) {
      setAutoScroll(false);
    }

    setShowScrollBtn(!isAtBottom);
  }, [autoScroll]);

  // -------------------------------------------------------------------------
  // Auto-scroll effect — fires when lines change
  // -------------------------------------------------------------------------

  React.useEffect(() => {
    if (!autoScroll) return;
    const el = viewportRef.current;
    if (!el) return;

    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [lines, autoScroll]);

  // -------------------------------------------------------------------------
  // Scroll to bottom button handler
  // -------------------------------------------------------------------------

  const scrollToBottom = React.useCallback(() => {
    const el = viewportRef.current;
    if (!el) return;

    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    setAutoScroll(true);
    setShowScrollBtn(false);
  }, []);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const isEmpty = lines.length === 0;

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-md',
        'border border-border/60',
        // Dark terminal background — slightly different from the card background
        // so it reads as a distinct "terminal pane"
        'bg-[hsl(var(--muted)/0.4)] dark:bg-zinc-950/80',
        className
      )}
      role="log"
      aria-live="polite"
      aria-label="Stage execution logs"
      aria-atomic="false"
    >
      {/* ------------------------------------------------------------------ */}
      {/* Scrollable viewport                                                 */}
      {/* ------------------------------------------------------------------ */}
      <div
        ref={viewportRef}
        onScroll={handleScroll}
        className="overflow-y-auto overscroll-contain"
        style={{ maxHeight }}
      >
        {isEmpty ? (
          <EmptyState />
        ) : (
          <div className="py-2 space-y-0">
            {lines.map((line, index) => (
              <LogLineRow
                // Use index as key — lines are append-only and positionally stable.
                // If lines had stable IDs, prefer those.
                key={index}
                line={line}
                lineNumber={index + 1}
                showLineNumbers={showLineNumbers}
              />
            ))}
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Scroll to bottom floating button                                    */}
      {/* ------------------------------------------------------------------ */}
      {showScrollBtn && (
        <Button
          size="icon"
          variant="secondary"
          onClick={scrollToBottom}
          aria-label="Scroll to bottom"
          className={cn(
            'absolute bottom-2 right-2 z-10 h-7 w-7 rounded-full shadow-md',
            'border border-border/60',
            'bg-background/90 hover:bg-background text-muted-foreground hover:text-foreground',
            'transition-all duration-150'
          )}
        >
          <ChevronDown className="h-4 w-4" aria-hidden="true" />
        </Button>
      )}
    </div>
  );
}
