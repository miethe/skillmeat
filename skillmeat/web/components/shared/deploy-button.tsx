'use client';

import { useState } from 'react';
import { Rocket, ChevronDown, Terminal, Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { DeployDialog } from '@/components/collection/deploy-dialog';
import { CliCommandSection } from '@/components/entity/cli-command-section';
import { useCliCopy } from '@/hooks';
import { generateBasicDeployCommand } from '@/lib/cli-commands';
import type { Artifact } from '@/types/artifact';

// ============================================================================
// Types
// ============================================================================

export interface DeployButtonProps {
  /** The artifact to deploy (null disables the button) */
  artifact: Artifact | null;
  /** Existing deployment paths for overwrite detection in DeployDialog */
  existingDeploymentPaths?: string[];
  /** Callback fired after a successful deployment */
  onDeploySuccess?: () => void;
  /** Visual variant for the button group */
  variant?: 'default' | 'outline';
  /** Size of the button group */
  size?: 'default' | 'sm';
  /** Additional CSS classes for the outer container */
  className?: string;
  /** Label override (default: "Deploy") */
  label?: string;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * DeployButton - Split-style deploy button with dropdown for CLI options
 *
 * Provides a unified deployment entry point with three actions:
 * 1. Primary click opens the DeployDialog for project-based deployment
 * 2. "Quick Deploy via CLI" copies the basic deploy command to clipboard
 * 3. "CLI Deploy Options..." opens a dialog with the full CliCommandSection
 *
 * @example
 * ```tsx
 * <DeployButton artifact={artifact} onDeploySuccess={handleRefresh} />
 *
 * <DeployButton
 *   artifact={artifact}
 *   variant="outline"
 *   size="sm"
 *   label="Deploy Skill"
 * />
 * ```
 */
export function DeployButton({
  artifact,
  existingDeploymentPaths,
  onDeploySuccess,
  variant = 'default',
  size = 'default',
  className,
  label = 'Deploy',
}: DeployButtonProps) {
  const [showDeployDialog, setShowDeployDialog] = useState(false);
  const [showCliDialog, setShowCliDialog] = useState(false);
  const { copied, copy } = useCliCopy();

  const isDisabled = !artifact;
  const artifactName = artifact?.name ?? '';

  const handlePrimaryClick = () => {
    if (!artifact) return;
    setShowDeployDialog(true);
  };

  const handleQuickCopy = async () => {
    if (!artifactName) return;
    const command = generateBasicDeployCommand(artifactName);
    await copy(command);
  };

  const handleDeployDialogClose = () => {
    setShowDeployDialog(false);
  };

  const handleDeploySuccess = () => {
    onDeploySuccess?.();
  };

  // Determine size-dependent classes
  const isSmall = size === 'sm';
  const mainPaddingClass = isSmall ? 'px-2.5 py-1.5 text-xs' : 'px-3 py-2 text-sm';
  const iconSize = isSmall ? 'h-3.5 w-3.5' : 'h-4 w-4';
  const chevronPaddingClass = isSmall ? 'px-1.5' : 'px-2';

  // Variant-dependent border/bg classes
  const isOutline = variant === 'outline';
  const disabledClasses = 'opacity-50 pointer-events-none';
  const separatorClass = isOutline
    ? 'border-l border-input'
    : 'border-l border-primary-foreground/20';

  return (
    <>
      {/* Split Button Group */}
      <div
        className={cn(
          'inline-flex items-center rounded-md',
          isOutline && 'border border-input',
          className
        )}
      >
        {/* Primary Deploy Button */}
        <button
          type="button"
          onClick={handlePrimaryClick}
          disabled={isDisabled}
          className={cn(
            'inline-flex items-center gap-1.5 font-medium transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
            mainPaddingClass,
            isOutline
              ? 'rounded-l-md bg-background hover:bg-accent hover:text-accent-foreground'
              : 'rounded-l-md bg-primary text-primary-foreground hover:bg-primary/90',
            isDisabled && disabledClasses
          )}
          aria-label={`Deploy ${artifactName}`}
        >
          <Rocket className={iconSize} aria-hidden="true" />
          {label}
        </button>

        {/* Separator + Dropdown Trigger */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              disabled={isDisabled}
              className={cn(
                'inline-flex items-center justify-center transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                chevronPaddingClass,
                isSmall ? 'py-1.5' : 'py-2',
                separatorClass,
                isOutline
                  ? 'rounded-r-md bg-background hover:bg-accent hover:text-accent-foreground'
                  : 'rounded-r-md bg-primary text-primary-foreground hover:bg-primary/90',
                isDisabled && disabledClasses
              )}
              aria-label="Deploy options"
            >
              <ChevronDown className={isSmall ? 'h-3 w-3' : 'h-3.5 w-3.5'} aria-hidden="true" />
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-52">
            <DropdownMenuItem onSelect={handlePrimaryClick}>
              <Rocket className="mr-2 h-4 w-4" aria-hidden="true" />
              Deploy to Project
            </DropdownMenuItem>

            <DropdownMenuSeparator />

            <DropdownMenuItem onSelect={handleQuickCopy}>
              {copied ? (
                <Check className="mr-2 h-4 w-4 text-green-500" aria-hidden="true" />
              ) : (
                <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
              )}
              Quick Deploy via CLI
            </DropdownMenuItem>

            <DropdownMenuItem onSelect={() => setShowCliDialog(true)}>
              <Terminal className="mr-2 h-4 w-4" aria-hidden="true" />
              CLI Deploy Options...
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Deploy Dialog */}
      <DeployDialog
        artifact={artifact}
        existingDeploymentPaths={existingDeploymentPaths}
        isOpen={showDeployDialog}
        onClose={handleDeployDialogClose}
        onSuccess={handleDeploySuccess}
      />

      {/* CLI Deploy Options Dialog */}
      <Dialog open={showCliDialog} onOpenChange={setShowCliDialog}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <DialogTitle>CLI Deploy Commands</DialogTitle>
            <DialogDescription>Copy deployment commands for {artifactName}</DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <CliCommandSection artifactName={artifactName} />
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCliDialog(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
