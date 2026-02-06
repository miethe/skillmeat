/**
 * KeyboardHelpModal Component (A11Y-3.12)
 *
 * Displays all available keyboard shortcuts for the Memory Inbox in a
 * categorized table layout. Triggered by pressing "?" or via a help button.
 *
 * Uses shadcn Dialog for accessible modal behavior with focus trapping
 * and Escape dismissal.
 */

'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface KeyboardHelpModalProps {
  /** Whether the modal is open. */
  open: boolean;
  /** Callback to control open state. */
  onOpenChange: (open: boolean) => void;
}

// ---------------------------------------------------------------------------
// Shortcut data
// ---------------------------------------------------------------------------

interface ShortcutEntry {
  keys: string[];
  description: string;
}

interface ShortcutGroup {
  label: string;
  shortcuts: ShortcutEntry[];
}

const SHORTCUT_GROUPS: ShortcutGroup[] = [
  {
    label: 'Navigation',
    shortcuts: [
      { keys: ['j'], description: 'Move to next item' },
      { keys: ['k'], description: 'Move to previous item' },
    ],
  },
  {
    label: 'Triage Actions',
    shortcuts: [
      { keys: ['a'], description: 'Approve focused item' },
      { keys: ['e'], description: 'Edit focused item' },
      { keys: ['r'], description: 'Reject focused item' },
      { keys: ['m'], description: 'Merge focused item' },
    ],
  },
  {
    label: 'Selection',
    shortcuts: [
      { keys: ['Space'], description: 'Toggle select focused item' },
      { keys: ['\u2318+A', 'Ctrl+A'], description: 'Select all visible items' },
    ],
  },
  {
    label: 'Detail',
    shortcuts: [
      { keys: ['Enter'], description: 'Open detail panel' },
      { keys: ['Escape'], description: 'Close panel / clear selection' },
    ],
  },
  {
    label: 'Help',
    shortcuts: [
      { keys: ['?'], description: 'Show this help dialog' },
    ],
  },
];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KeyBadge({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-flex items-center justify-center min-w-[24px] h-6 px-1.5 rounded border border-border bg-muted font-mono text-xs text-foreground shadow-sm">
      {children}
    </kbd>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * KeyboardHelpModal -- accessible overlay showing all keyboard shortcuts.
 *
 * @example
 * ```tsx
 * <KeyboardHelpModal open={helpOpen} onOpenChange={setHelpOpen} />
 * ```
 */
export function KeyboardHelpModal({ open, onOpenChange }: KeyboardHelpModalProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Navigate and triage memory items without leaving the keyboard.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-2 space-y-5">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.label}>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                {group.label}
              </h3>
              <div className="space-y-1.5">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.description}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-sm text-foreground">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, i) => (
                        <span key={key} className="flex items-center gap-1">
                          {i > 0 && (
                            <span className="text-xs text-muted-foreground">/</span>
                          )}
                          <KeyBadge>{key}</KeyBadge>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
