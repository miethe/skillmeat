/**
 * Tab Content Wrapper Component
 *
 * A content wrapper for tab content with proper scrolling behavior.
 * Uses shadcn TabsContent and ScrollArea for consistent modal tab content.
 *
 * @example Basic usage
 * ```tsx
 * <Tabs value={activeTab}>
 *   <TabNavigation tabs={tabs} />
 *   <TabContentWrapper value="overview">
 *     <p>Overview content here</p>
 *   </TabContentWrapper>
 *   <TabContentWrapper value="settings" scrollable={false}>
 *     <SettingsForm />
 *   </TabContentWrapper>
 * </Tabs>
 * ```
 *
 * @example With custom height
 * ```tsx
 * <TabContentWrapper
 *   value="files"
 *   className="h-[60vh]"
 * >
 *   <FileList />
 * </TabContentWrapper>
 * ```
 */

'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { TabsContent } from '@/components/ui/tabs';
import { ScrollArea } from '@/components/ui/scroll-area';

// ============================================================================
// Types
// ============================================================================

export interface TabContentWrapperProps {
  /** Tab value this content corresponds to */
  value: string;
  /** Content to render inside the tab */
  children: React.ReactNode;
  /** Additional CSS classes for the outer container */
  className?: string;
  /** Whether content should be scrollable (default: true) */
  scrollable?: boolean;
}

// ============================================================================
// Component
// ============================================================================

/**
 * TabContentWrapper - Scrollable container for modal tab content
 *
 * Wraps tab content with:
 * - TabsContent for proper tab switching
 * - Optional ScrollArea for scrollable content
 * - Consistent height calculation for modal use
 * - Proper padding and spacing
 *
 * @param value - Tab identifier that matches the TabsTrigger value
 * @param children - Content to render
 * @param className - Additional CSS classes
 * @param scrollable - Whether to wrap content in ScrollArea (default: true)
 */
export function TabContentWrapper({
  value,
  children,
  className,
  scrollable = true,
}: TabContentWrapperProps) {
  // Inner content with consistent padding
  const content = (
    <div className="space-y-4 px-6 py-4">
      {children}
    </div>
  );

  return (
    <TabsContent
      value={value}
      className={cn(
        // Remove default margin from TabsContent
        'mt-0',
        // Default height for modal content (90vh modal - header/tabs ~12rem)
        scrollable && 'h-[calc(90vh-12rem)]',
        // Focus styles
        'focus-visible:outline-none focus-visible:ring-0',
        className
      )}
    >
      {scrollable ? (
        <ScrollArea className="h-full">
          {content}
        </ScrollArea>
      ) : (
        content
      )}
    </TabsContent>
  );
}
