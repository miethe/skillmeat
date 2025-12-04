/**
 * useFocusTrap Hook
 *
 * Traps focus within a container when active, cycling through focusable elements.
 * Useful for modals, dialogs, and dropdown panels to ensure keyboard accessibility.
 *
 * @param isActive - Whether focus trap is currently active
 * @returns containerRef - Ref to attach to the container element
 *
 * @example
 * ```tsx
 * function MyDialog({ isOpen }: { isOpen: boolean }) {
 *   const containerRef = useFocusTrap(isOpen);
 *
 *   return (
 *     <div ref={containerRef} role="dialog">
 *       <button>First</button>
 *       <button>Last</button>
 *     </div>
 *   );
 * }
 * ```
 */

import { useEffect, useRef } from 'react';

const FOCUSABLE_ELEMENTS_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ');

export function useFocusTrap(isActive: boolean) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isActive || !containerRef.current) return;

    const container = containerRef.current;

    // Get all focusable elements within the container
    const focusableElements = Array.from(
      container.querySelectorAll<HTMLElement>(FOCUSABLE_ELEMENTS_SELECTOR)
    );

    if (focusableElements.length === 0) return;

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];

    // Focus the first element when trap becomes active
    const timeoutId = setTimeout(() => {
      firstElement?.focus();
    }, 0);

    // Handle keyboard navigation
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;

      // Shift+Tab on first element -> cycle to last
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement?.focus();
      }
      // Tab on last element -> cycle to first
      else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement?.focus();
      }
    };

    // Attach event listener
    container.addEventListener('keydown', handleKeyDown);

    // Cleanup
    return () => {
      clearTimeout(timeoutId);
      container.removeEventListener('keydown', handleKeyDown);
    };
  }, [isActive]);

  return containerRef;
}
