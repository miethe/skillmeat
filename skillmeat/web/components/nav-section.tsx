'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { LucideIcon } from 'lucide-react';

// ============================================================================
// Types
// ============================================================================

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

interface NavSectionProps {
  title: string;
  icon: LucideIcon;
  items: NavItem[];
  defaultExpanded?: boolean;
  storageKey?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Check if localStorage is available (handles SSR and privacy modes)
 */
function isStorageAvailable(): boolean {
  if (typeof window === 'undefined') return false;

  try {
    const test = '__storage_test__';
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch {
    return false;
  }
}

/**
 * Load expanded state from localStorage
 */
function loadExpandedState(storageKey: string): boolean | null {
  if (!isStorageAvailable()) return null;

  try {
    const stored = localStorage.getItem(`nav-section-${storageKey}`);
    if (stored === null) return null;
    return stored === 'true';
  } catch {
    return null;
  }
}

/**
 * Save expanded state to localStorage
 */
function saveExpandedState(storageKey: string, expanded: boolean): void {
  if (!isStorageAvailable()) return;

  try {
    localStorage.setItem(`nav-section-${storageKey}`, String(expanded));
  } catch {
    // Silently fail if storage is unavailable
  }
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * NavSection - Collapsible navigation section component
 *
 * Features:
 * - Expand/collapse with smooth animation
 * - Auto-expand if child route is active
 * - localStorage persistence for state
 * - Full keyboard accessibility
 * - ARIA attributes for screen readers
 *
 * @example
 * ```tsx
 * <NavSection
 *   title="Collections"
 *   icon={FolderOpen}
 *   storageKey="collections"
 *   defaultExpanded={true}
 *   items={[
 *     { name: 'Browse', href: '/collection', icon: Grid3X3 },
 *     { name: 'Manage', href: '/manage', icon: Settings2 }
 *   ]}
 * />
 * ```
 */
export function NavSection({
  title,
  icon: Icon,
  items,
  defaultExpanded = false,
  storageKey,
}: NavSectionProps) {
  const pathname = usePathname();

  // Check if any child route is active
  const isChildActive = items.some(
    (item) => pathname === item.href || pathname.startsWith(`${item.href}/`)
  );

  // Initialize expanded state
  const [isExpanded, setIsExpanded] = useState<boolean>(() => {
    // Priority: localStorage > active child > defaultExpanded
    if (storageKey) {
      const stored = loadExpandedState(storageKey);
      if (stored !== null) return stored;
    }
    return isChildActive || defaultExpanded;
  });

  // Auto-expand if child becomes active
  useEffect(() => {
    if (isChildActive && !isExpanded) {
      setIsExpanded(true);
      if (storageKey) {
        saveExpandedState(storageKey, true);
      }
    }
  }, [isChildActive, isExpanded, storageKey]);

  // Toggle handler
  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => {
      const next = !prev;
      if (storageKey) {
        saveExpandedState(storageKey, next);
      }
      return next;
    });
  }, [storageKey]);

  // Keyboard handler
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleToggle();
      }
    },
    [handleToggle]
  );

  return (
    <div>
      {/* Section Header */}
      <button
        type="button"
        role="button"
        aria-expanded={isExpanded}
        aria-controls={storageKey ? `nav-section-${storageKey}-content` : undefined}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        className={cn(
          'flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
          'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
        )}
      >
        <Icon className="h-4 w-4 flex-shrink-0" />
        <span className="flex-1 text-left">{title}</span>
        <ChevronDown
          className={cn(
            'h-4 w-4 flex-shrink-0 transition-transform duration-200',
            isExpanded ? 'rotate-180' : 'rotate-0'
          )}
          aria-hidden="true"
        />
      </button>

      {/* Section Content */}
      <div
        id={storageKey ? `nav-section-${storageKey}-content` : undefined}
        className={cn(
          'overflow-hidden transition-all duration-200 ease-in-out',
          isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="space-y-1 pl-4 pt-1">
          {items.map((item) => {
            const ItemIcon = item.icon;
            const isActive =
              pathname === item.href || pathname.startsWith(`${item.href}/`);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-secondary text-secondary-foreground font-medium'
                    : 'text-muted-foreground hover:bg-secondary/50 hover:text-foreground',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
                )}
              >
                <ItemIcon className="h-4 w-4 flex-shrink-0" />
                {item.name}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
