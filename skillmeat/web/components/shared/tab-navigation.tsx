/**
 * Tab Navigation Component
 *
 * A styled tab list for modal tabs with underline style (not rounded).
 * Uses shadcn Tabs primitives with custom styling for consistent modal navigation.
 *
 * @example Basic usage
 * ```tsx
 * <Tabs value={activeTab} onValueChange={setActiveTab}>
 *   <TabNavigation
 *     tabs={[
 *       { value: 'overview', label: 'Overview' },
 *       { value: 'settings', label: 'Settings' },
 *     ]}
 *   />
 *   <TabsContent value="overview">...</TabsContent>
 *   <TabsContent value="settings">...</TabsContent>
 * </Tabs>
 * ```
 *
 * @example With icons and badges
 * ```tsx
 * <TabNavigation
 *   tabs={[
 *     { value: 'overview', label: 'Overview', icon: Info },
 *     { value: 'files', label: 'Files', icon: FileText, badge: 12 },
 *     { value: 'disabled', label: 'Coming Soon', disabled: true },
 *   ]}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';

// ============================================================================
// Types
// ============================================================================

export interface Tab {
  /** Unique identifier for the tab */
  value: string;
  /** Display label for the tab */
  label: string;
  /** Optional icon component */
  icon?: React.ComponentType<{ className?: string }>;
  /** Optional badge count to display */
  badge?: number;
  /** Whether the tab is disabled */
  disabled?: boolean;
}

export interface TabNavigationProps {
  /** Array of tab configurations */
  tabs: Tab[];
  /** Additional CSS classes for the TabsList container */
  className?: string;
  /** Accessible label for the tab list */
  ariaLabel?: string;
}

// ============================================================================
// Component
// ============================================================================

/**
 * TabNavigation - Underline-styled tab list for modals
 *
 * Renders a horizontal tab list with underline styling instead of
 * the default rounded pill style. Supports icons, badges, and disabled states.
 *
 * Must be used within a Tabs component from shadcn/ui.
 *
 * @param tabs - Array of tab configurations
 * @param className - Additional CSS classes for the container
 * @param ariaLabel - Accessible label for the tab list
 */
export function TabNavigation({ tabs, className, ariaLabel = 'Navigation tabs' }: TabNavigationProps) {
  return (
    <TabsList
      className={cn(
        // Override default rounded/background styling for underline style
        'h-auto w-full justify-start gap-0 rounded-none border-b bg-transparent p-0',
        className
      )}
      aria-label={ariaLabel}
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;

        return (
          <TabsTrigger
            key={tab.value}
            value={tab.value}
            disabled={tab.disabled}
            className={cn(
              // Base styles
              'relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium',
              // Remove default rounded styling
              'rounded-none border-b-2 border-transparent bg-transparent shadow-none',
              // Active state - underline instead of background
              'data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-foreground data-[state=active]:shadow-none',
              // Inactive/hover states
              'text-muted-foreground hover:text-foreground',
              // Disabled state
              'disabled:cursor-not-allowed disabled:opacity-50',
              // Focus ring
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
            )}
            aria-label={tab.badge !== undefined && tab.badge > 0 ? `${tab.label}, ${tab.badge} items` : undefined}
          >
            {Icon && (
              <Icon className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
            )}
            <span>{tab.label}</span>
            {typeof tab.badge === 'number' && tab.badge > 0 && (
              <Badge
                variant="secondary"
                className="ml-1 h-5 min-w-[1.25rem] px-1.5 text-xs"
                aria-hidden="true"
              >
                {tab.badge > 99 ? '99+' : tab.badge}
              </Badge>
            )}
          </TabsTrigger>
        );
      })}
    </TabsList>
  );
}
