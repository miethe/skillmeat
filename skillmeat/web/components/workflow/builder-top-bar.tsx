/**
 * BuilderTopBar Component
 *
 * Sticky header for the workflow builder page. Sits directly below the
 * global app header and provides navigation, inline name editing, dirty
 * state signalling, and save actions.
 *
 * @example
 * ```tsx
 * <BuilderTopBar
 *   name={workflow.name}
 *   isDirty={isDirty}
 *   isSaving={isSaving}
 *   onNameChange={(name) => dispatch({ type: 'SET_NAME', payload: name })}
 *   onSaveDraft={handleSaveDraft}
 *   onSaveAndClose={handleSaveAndClose}
 *   onBack={() => router.back()}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { InlineEdit } from '@/components/shared/inline-edit';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

export interface BuilderTopBarProps {
  /** Current workflow name */
  name: string;
  /** Whether there are unsaved changes */
  isDirty: boolean;
  /** Whether a save operation is in progress */
  isSaving: boolean;
  /** Called when the user commits a name change */
  onNameChange: (name: string) => void;
  /** Called when the user clicks "Save Draft" */
  onSaveDraft: () => void;
  /** Called when the user clicks "Save & Close" */
  onSaveAndClose: () => void;
  /** Called when the user clicks the back button */
  onBack: () => void;
  /** Additional CSS classes for the outer element */
  className?: string;
}

// ============================================================================
// Sub-components
// ============================================================================

/** Amber unsaved-changes indicator — dot + label */
function UnsavedIndicator() {
  return (
    <span
      role="status"
      aria-live="polite"
      aria-label="Unsaved changes"
      className={cn(
        'flex items-center gap-1.5',
        // Fade-in when it appears
        'animate-in fade-in duration-200'
      )}
    >
      {/* Amber dot */}
      <span
        aria-hidden="true"
        className={cn(
          'block h-2 w-2 flex-shrink-0 rounded-full',
          'bg-amber-400 dark:bg-amber-500',
          // Subtle pulse to draw attention without being intrusive
          'animate-pulse'
        )}
      />
      <span className="text-xs font-medium text-amber-600 dark:text-amber-400 whitespace-nowrap">
        Unsaved changes
      </span>
    </span>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * BuilderTopBar — sticky header for the workflow builder canvas.
 *
 * Layout (left → right):
 *   [Back button] [Workflow name (InlineEdit)] [Unsaved indicator] [Save Draft] [Save & Close]
 *
 * Accessibility:
 * - Back button has explicit aria-label
 * - Unsaved indicator uses role="status" with aria-live="polite"
 * - Save buttons are disabled with descriptive text when not actionable
 * - InlineEdit manages its own aria-label internally
 */
export function BuilderTopBar({
  name,
  isDirty,
  isSaving,
  onNameChange,
  onSaveDraft,
  onSaveAndClose,
  onBack,
  className,
}: BuilderTopBarProps) {
  const actionsDisabled = !isDirty || isSaving;

  return (
    <header
      className={cn(
        // Sticky positioning below global app header
        'sticky top-0 z-10',
        // Background + bottom rule
        'bg-background border-b border-border',
        // Layout: single horizontal band, vertically centred
        'flex items-center gap-3 px-4 py-2',
        // Prevent content overflow on narrow viewports
        'min-w-0',
        className
      )}
    >
      {/* ── Back button ─────────────────────────────────────────────── */}
      <Button
        variant="ghost"
        size="sm"
        onClick={onBack}
        aria-label="Go back to workflow list"
        className={cn(
          'flex-shrink-0 h-8 w-8 p-0',
          'text-muted-foreground hover:text-foreground',
          'transition-colors'
        )}
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
      </Button>

      {/* Vertical divider — visual separation between nav and content */}
      <div
        className="h-5 w-px flex-shrink-0 bg-border"
        aria-hidden="true"
      />

      {/* ── Workflow name ────────────────────────────────────────────── */}
      {/*
       * min-w-0 + flex-1 lets the name region shrink gracefully so the
       * action buttons always remain visible on narrow viewports.
       */}
      <div className="min-w-0 flex-1">
        <InlineEdit
          as="h2"
          value={name}
          onChange={onNameChange}
          placeholder="Untitled Workflow"
          className={cn(
            'text-base font-semibold leading-tight tracking-tight',
            // Truncate long names in display mode
            'max-w-[40ch] truncate'
          )}
          inputClassName="h-8 text-base font-semibold"
        />
      </div>

      {/* ── Right-side controls ──────────────────────────────────────── */}
      <div className="flex flex-shrink-0 items-center gap-2">
        {/* Unsaved indicator — only rendered when dirty */}
        {isDirty && !isSaving && <UnsavedIndicator />}

        {/* Saving in-progress label — replaces unsaved indicator while saving */}
        {isSaving && (
          <span
            role="status"
            aria-live="polite"
            className="text-xs text-muted-foreground animate-in fade-in duration-150 whitespace-nowrap"
          >
            Saving…
          </span>
        )}

        {/* Save Draft */}
        <Button
          variant="outline"
          size="sm"
          onClick={onSaveDraft}
          disabled={actionsDisabled}
          aria-label={
            isSaving
              ? 'Save in progress'
              : !isDirty
                ? 'No changes to save'
                : 'Save draft without closing'
          }
          className="h-8 text-sm"
        >
          Save Draft
        </Button>

        {/* Save & Close */}
        <Button
          variant="default"
          size="sm"
          onClick={onSaveAndClose}
          disabled={actionsDisabled}
          aria-label={
            isSaving
              ? 'Save in progress'
              : !isDirty
                ? 'No changes to save'
                : 'Save changes and close the builder'
          }
          className="h-8 text-sm"
        >
          Save &amp; Close
        </Button>
      </div>
    </header>
  );
}
