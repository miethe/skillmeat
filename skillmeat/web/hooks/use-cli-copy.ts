/**
 * Custom hook for clipboard copy operations with feedback state
 *
 * Manages clipboard copy operations with automatic state reset for UI feedback.
 * Commonly used for CLI commands, share links, and other copyable content.
 *
 * @example
 * ```tsx
 * function CommandDisplay({ command }: { command: string }) {
 *   const { copied, copy } = useCliCopy();
 *
 *   return (
 *     <div className="flex items-center gap-2">
 *       <code>{command}</code>
 *       <Button onClick={() => copy(command)}>
 *         {copied ? <Check /> : <Copy />}
 *       </Button>
 *     </div>
 *   );
 * }
 * ```
 */

import { useState, useCallback } from 'react';

/** Reset delay for copied state in milliseconds */
const COPY_FEEDBACK_DURATION = 2000;

/**
 * Hook for managing clipboard copy operations with feedback state
 *
 * @returns Object containing:
 *   - `copied`: boolean indicating if copy was successful (resets after 2s)
 *   - `copy`: async function to copy text to clipboard
 *
 * @example
 * const { copied, copy } = useCliCopy();
 * await copy('skillmeat deploy my-artifact');
 * // copied is true for 2 seconds after successful copy
 */
export function useCliCopy(): {
  copied: boolean;
  copy: (text: string) => Promise<void>;
} {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async (text: string): Promise<void> => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), COPY_FEEDBACK_DURATION);
    } catch (error) {
      console.error('Failed to copy to clipboard:', error);
    }
  }, []);

  return { copied, copy };
}
