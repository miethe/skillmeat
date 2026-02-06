'use client';

import { useState } from 'react';
import { ChevronUp, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible';
import { useCliCopy } from '@/hooks';
import { CliCommandSection, getCommandForOption } from './cli-command-section';

// ============================================================================
// Types
// ============================================================================

/**
 * Props for CollapsibleActionBar component
 */
export interface CollapsibleActionBarProps {
  /** The artifact name to generate CLI commands for */
  artifactName: string;
  /** Whether the action bar is open by default (defaults to true) */
  defaultOpen?: boolean;
  /** Optional className for additional styling */
  className?: string;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * CollapsibleActionBar - Bottom action bar with collapsible CLI command section
 *
 * Provides progressive disclosure for CLI deploy commands. Features a floating
 * chevron toggle at the top center that sits on the border.
 *
 * @example
 * ```tsx
 * // Basic usage - defaults to open
 * <CollapsibleActionBar artifactName="my-skill" />
 *
 * // Start collapsed
 * <CollapsibleActionBar artifactName="my-skill" defaultOpen={false} />
 * ```
 */
export function CollapsibleActionBar({
  artifactName,
  defaultOpen = true,
  className,
}: CollapsibleActionBarProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [selectedCommand, setSelectedCommand] = useState<string>('basic');
  const { copied, copy } = useCliCopy();

  // Get the current command based on selection
  const currentCommand = getCommandForOption(artifactName, selectedCommand);

  // Handle copy button click
  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent triggering collapse toggle
    await copy(currentCommand);
  };

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className={cn('relative border-t border-border bg-background', className)}
    >
      {/* Floating Chevron Toggle - Centered on top border */}
      <CollapsibleTrigger asChild>
        <button
          type="button"
          className={cn(
            'absolute left-1/2 -translate-x-1/2 -translate-y-1/2',
            'z-10 flex h-6 w-6 items-center justify-center',
            'rounded-full border border-border bg-muted',
            'transition-all duration-200',
            'hover:border-accent-foreground/20 hover:bg-accent',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
          )}
          aria-label={isOpen ? 'Collapse CLI command section' : 'Expand CLI command section'}
        >
          <ChevronUp
            className={cn(
              'h-3.5 w-3.5 text-muted-foreground transition-transform duration-200',
              isOpen && 'rotate-180'
            )}
            aria-hidden="true"
          />
        </button>
      </CollapsibleTrigger>

      {/* Main Trigger Area - Click anywhere to toggle */}
      <CollapsibleTrigger asChild>
        <div
          className={cn(
            'flex w-full cursor-pointer items-center justify-between px-4 py-3 pt-4',
            'transition-colors hover:bg-accent/30'
          )}
          role="button"
          tabIndex={-1} // Not focusable since the chevron button handles keyboard
        >
          <span className="text-sm font-medium text-foreground">CLI Deploy Command</span>

          {/* Copy button - Always visible */}
          <Button
            variant="outline"
            size="icon"
            onClick={handleCopy}
            aria-label="Copy CLI command"
            className="shrink-0"
          >
            {copied ? (
              <Check className="h-4 w-4 text-green-500" aria-hidden="true" />
            ) : (
              <Copy className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        </div>
      </CollapsibleTrigger>

      {/* Collapsible Content */}
      <CollapsibleContent
        className={cn(
          'overflow-hidden',
          'data-[state=open]:animate-in data-[state=closed]:animate-out',
          'data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0',
          'data-[state=closed]:slide-out-to-top-2 data-[state=open]:slide-in-from-top-2'
        )}
      >
        <CliCommandSection
          artifactName={artifactName}
          className="px-4 pb-4 pt-0"
          hideLabel
          hideCopyButton
          value={selectedCommand}
          onValueChange={setSelectedCommand}
        />
      </CollapsibleContent>
    </Collapsible>
  );
}
