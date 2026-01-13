/**
 * Custom hook for detecting element intersection using IntersectionObserver API
 *
 * Useful for implementing infinite scroll, lazy loading, and visibility tracking.
 *
 * @example
 * ```tsx
 * const { targetRef, isIntersecting } = useIntersectionObserver({
 *   rootMargin: '100px',
 *   enabled: hasNextPage,
 * });
 *
 * useEffect(() => {
 *   if (isIntersecting) {
 *     fetchNextPage();
 *   }
 * }, [isIntersecting, fetchNextPage]);
 *
 * return (
 *   <div>
 *     {items.map(item => <Item key={item.id} {...item} />)}
 *     <div ref={targetRef} />
 *   </div>
 * );
 * ```
 */

import { useEffect, useRef, useState } from 'react';

export interface UseIntersectionObserverOptions {
  /**
   * Threshold at which the observer's callback is executed
   * A value of 0 means as soon as even one pixel is visible
   * @default 0
   */
  threshold?: number;
  /**
   * Margin around the root element
   * Use positive values to trigger before element enters viewport
   * @default '100px'
   */
  rootMargin?: string;
  /**
   * Whether the observer should be active
   * Disable when there's nothing more to load
   * @default true
   */
  enabled?: boolean;
}

export interface UseIntersectionObserverResult<T extends HTMLElement = HTMLDivElement> {
  /**
   * Ref to attach to the target element
   */
  targetRef: React.RefObject<T | null>;
  /**
   * Whether the target element is currently intersecting
   */
  isIntersecting: boolean;
}

export function useIntersectionObserver<T extends HTMLElement = HTMLDivElement>(
  options: UseIntersectionObserverOptions = {}
): UseIntersectionObserverResult<T> {
  const { threshold = 0, rootMargin = '100px', enabled = true } = options;
  const [isIntersecting, setIsIntersecting] = useState(false);
  const targetRef = useRef<T>(null);

  useEffect(() => {
    const target = targetRef.current;
    if (!target || !enabled) {
      setIsIntersecting(false);
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const entry = entries[0];
        if (entry) {
          setIsIntersecting(entry.isIntersecting);
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(target);

    return () => {
      observer.disconnect();
    };
  }, [threshold, rootMargin, enabled]);

  return { targetRef, isIntersecting };
}
