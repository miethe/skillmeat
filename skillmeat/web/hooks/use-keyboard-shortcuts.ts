'use client';

/**
 * useKeyboardShortcuts Hook (A11Y-3.12)
 *
 * Attaches keyboard event listeners to a container ref for triage-oriented
 * keyboard navigation in the Memory Inbox. Implements the shortcut table
 * from design spec section 3.8.
 *
 * Shortcuts are disabled when:
 * - The `enabled` parameter is false (e.g., a modal/dialog is open)
 * - The active element is an input, textarea, select, or contenteditable
 *
 * Key bindings:
 * - j/k: Navigate down/up through memory items
 * - a/e/r/m: Approve, edit, reject, merge focused item
 * - Space: Toggle selection of focused item
 * - Enter: Open detail panel for focused item
 * - Escape: Close detail panel or clear selection
 * - Cmd+A / Ctrl+A: Select all visible items
 * - ?: Show keyboard shortcuts help overlay
 */

import { useEffect, useCallback } from 'react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface KeyboardShortcutActions {
  /** Navigate focus to the next item (j). */
  onNavigateDown: () => void;
  /** Navigate focus to the previous item (k). */
  onNavigateUp: () => void;
  /** Approve the focused item (a). */
  onApprove: () => void;
  /** Open the edit panel for the focused item (e). */
  onEdit: () => void;
  /** Reject the focused item (r). */
  onReject: () => void;
  /** Open the merge dialog for the focused item (m). */
  onMerge: () => void;
  /** Toggle selection of the focused item (Space). */
  onToggleSelect: () => void;
  /** Open the detail panel for the focused item (Enter). */
  onOpenDetail: () => void;
  /** Close the detail panel or clear selection (Escape). */
  onDismiss: () => void;
  /** Select all visible items (Cmd+A / Ctrl+A). */
  onSelectAll: () => void;
  /** Show keyboard shortcuts help overlay (?). */
  onShowHelp: () => void;
  /** Total number of items for navigation bounds checking. */
  itemCount: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Returns true if the currently active element is an interactive form control
 * where single-key shortcuts should be suppressed.
 */
function isEditableElement(element: Element | null): boolean {
  if (!element) return false;
  const tagName = element.tagName;
  if (tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT') {
    return true;
  }
  if (element.getAttribute('contenteditable') === 'true') {
    return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Attaches keyboard shortcut listeners to a container element.
 *
 * @param containerRef - React ref pointing to the keyboard-navigable container
 * @param actions - Callback functions for each keyboard shortcut
 * @param enabled - Set to false to disable all shortcuts (e.g., when a modal is open)
 *
 * @example
 * ```tsx
 * const containerRef = useRef<HTMLDivElement>(null);
 * useKeyboardShortcuts(containerRef, {
 *   onNavigateDown: () => setFocusedIndex(prev => Math.min(prev + 1, items.length - 1)),
 *   onNavigateUp: () => setFocusedIndex(prev => Math.max(prev - 1, 0)),
 *   onApprove: () => handleApprove(focusedId),
 *   // ...
 *   itemCount: items.length,
 * }, !anyModalOpen);
 * ```
 */
export function useKeyboardShortcuts(
  containerRef: React.RefObject<HTMLElement | null>,
  actions: KeyboardShortcutActions,
  enabled: boolean = true
): void {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      // Bail out if shortcuts are disabled
      if (!enabled) return;

      // Bail out if the user is typing in a form field
      if (isEditableElement(document.activeElement)) return;

      const key = event.key;
      const isMetaOrCtrl = event.metaKey || event.ctrlKey;

      // Cmd+A / Ctrl+A: Select all
      if (isMetaOrCtrl && (key === 'a' || key === 'A')) {
        event.preventDefault();
        actions.onSelectAll();
        return;
      }

      // Ignore other combos with meta/ctrl/alt to avoid hijacking browser shortcuts
      if (isMetaOrCtrl || event.altKey) return;

      switch (key) {
        case 'j':
          actions.onNavigateDown();
          break;

        case 'k':
          actions.onNavigateUp();
          break;

        case 'a':
          actions.onApprove();
          break;

        case 'e':
          actions.onEdit();
          break;

        case 'r':
          actions.onReject();
          break;

        case 'm':
          actions.onMerge();
          break;

        case ' ':
          event.preventDefault();
          actions.onToggleSelect();
          break;

        case 'Enter':
          actions.onOpenDetail();
          break;

        case 'Escape':
          actions.onDismiss();
          break;

        case '?':
          actions.onShowHelp();
          break;

        default:
          // Unrecognized key -- do nothing
          return;
      }
    },
    [enabled, actions]
  );

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !enabled) return;

    container.addEventListener('keydown', handleKeyDown);
    return () => {
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [containerRef, handleKeyDown, enabled]);
}
