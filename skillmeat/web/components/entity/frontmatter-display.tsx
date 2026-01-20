'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

// ============================================================================
// Types
// ============================================================================

export interface FrontmatterDisplayProps {
  /** Parsed YAML frontmatter object */
  frontmatter: Record<string, unknown>;
  /** Whether to start collapsed. Default: false (expanded) */
  defaultCollapsed?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Render a single value based on its type
 */
function renderValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) {
    return <span className="italic text-muted-foreground">null</span>;
  }

  if (typeof value === 'boolean') {
    return <span className="text-muted-foreground">{value ? 'true' : 'false'}</span>;
  }

  if (typeof value === 'number') {
    return <span>{value}</span>;
  }

  if (typeof value === 'string') {
    return <span>{value}</span>;
  }

  if (Array.isArray(value)) {
    // Render arrays as comma-separated values
    const stringValues = value.map((item) => {
      if (typeof item === 'object' && item !== null) {
        return JSON.stringify(item);
      }
      return String(item);
    });
    return <span>{stringValues.join(', ')}</span>;
  }

  if (typeof value === 'object') {
    // For nested objects, render as indented key-value pairs (1 level only)
    return (
      <div className="ml-4 mt-1 space-y-1">
        {Object.entries(value as Record<string, unknown>).map(([nestedKey, nestedValue]) => (
          <div key={nestedKey} className="text-sm">
            <strong className="font-medium text-muted-foreground">{nestedKey}</strong>:{' '}
            {typeof nestedValue === 'object' && nestedValue !== null
              ? JSON.stringify(nestedValue)
              : String(nestedValue ?? '')}
          </div>
        ))}
      </div>
    );
  }

  return <span>{String(value)}</span>;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * FrontmatterDisplay - Collapsible display for YAML frontmatter
 *
 * Displays parsed YAML frontmatter as key-value pairs with support for:
 * - Arrays rendered as comma-separated values
 * - Nested objects (1 level) rendered as indented key-value pairs
 * - Collapsible with expand/collapse toggle
 * - Max height with scrollable content
 *
 * @example
 * ```tsx
 * const frontmatter = {
 *   title: 'My Document',
 *   tags: ['react', 'typescript'],
 *   author: { name: 'John', email: 'john@example.com' }
 * };
 *
 * <FrontmatterDisplay
 *   frontmatter={frontmatter}
 *   defaultCollapsed={false}
 * />
 * ```
 */
export function FrontmatterDisplay({
  frontmatter,
  defaultCollapsed = false,
  className,
}: FrontmatterDisplayProps) {
  const [isOpen, setIsOpen] = useState(!defaultCollapsed);

  const entries = Object.entries(frontmatter);

  if (entries.length === 0) {
    return null;
  }

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn('rounded-md border border-border bg-muted/30 p-3', className)}
    >
      {/* Header with title and toggle button */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium text-foreground">Frontmatter</h4>
        <CollapsibleTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
            aria-label={isOpen ? 'Hide frontmatter' : 'Show frontmatter'}
          >
            {isOpen ? (
              <>
                <ChevronUp className="mr-1 h-4 w-4" aria-hidden="true" />
                Hide
              </>
            ) : (
              <>
                <ChevronDown className="mr-1 h-4 w-4" aria-hidden="true" />
                Show
              </>
            )}
          </Button>
        </CollapsibleTrigger>
      </div>

      {/* Collapsible content with smooth animation */}
      <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-collapsible-up data-[state=open]:animate-collapsible-down">
        <div className="mt-3 max-h-[300px] space-y-2 overflow-y-auto pr-1">
          {entries.map(([key, value]) => (
            <div key={key} className="text-sm">
              <strong className="font-medium">{key}</strong>: {renderValue(value)}
            </div>
          ))}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
