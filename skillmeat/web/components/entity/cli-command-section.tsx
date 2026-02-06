'use client';

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useCliCopy } from '@/hooks';
import {
  generateBasicDeployCommand,
  generateDeployWithOverwriteCommand,
  generateDeployWithProjectCommand,
} from '@/lib/cli-commands';

// ============================================================================
// Types
// ============================================================================

/**
 * Command option configuration for the select dropdown
 */
export interface CommandOption {
  /** Display label for the option */
  label: string;
  /** Unique value identifier */
  value: string;
  /** Optional description for the option */
  description?: string;
}

/**
 * Props for CliCommandSection component
 */
export interface CliCommandSectionProps {
  /** The artifact name to generate commands for */
  artifactName: string;
  /** Optional custom command options (defaults to basic/overwrite/project) */
  commandOptions?: CommandOption[];
  /** Optional className for additional styling */
  className?: string;
  /** Hide the label (useful when label is shown elsewhere, e.g., in a collapsible trigger) */
  hideLabel?: boolean;
  /** Hide the copy button (when copy is handled externally) */
  hideCopyButton?: boolean;
  /** Controlled value for selected command */
  value?: string;
  /** Callback when selected command changes (for controlled mode) */
  onValueChange?: (value: string) => void;
}

// ============================================================================
// Constants
// ============================================================================

/**
 * Default command options when none are provided
 */
export const DEFAULT_COMMAND_OPTIONS: CommandOption[] = [
  {
    label: 'Basic Deploy',
    value: 'basic',
    description: 'Simple deployment',
  },
  {
    label: 'With Overwrite',
    value: 'overwrite',
    description: 'Overwrite existing artifact',
  },
  {
    label: 'With Project Path',
    value: 'project',
    description: 'Deploy to specific project',
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Generate the CLI command based on the selected option and artifact name
 */
export function getCommandForOption(artifactName: string, optionValue: string): string {
  switch (optionValue) {
    case 'overwrite':
      return generateDeployWithOverwriteCommand(artifactName);
    case 'project':
      return generateDeployWithProjectCommand(artifactName);
    case 'basic':
    default:
      return generateBasicDeployCommand(artifactName);
  }
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * CliCommandSection - Reusable component to display CLI deploy commands
 *
 * Displays a CLI command section with:
 * - Select dropdown for command variant selection
 * - Monospace code display for the command
 * - Copy button with feedback state
 *
 * @example
 * ```tsx
 * // Basic usage with default command options
 * <CliCommandSection artifactName="my-awesome-skill" />
 *
 * // Custom command options
 * <CliCommandSection
 *   artifactName="my-skill"
 *   commandOptions={[
 *     { label: 'Install', value: 'install' },
 *     { label: 'Update', value: 'update' },
 *   ]}
 * />
 * ```
 */
export function CliCommandSection({
  artifactName,
  commandOptions = DEFAULT_COMMAND_OPTIONS,
  className,
  hideLabel = false,
  hideCopyButton = false,
  value,
  onValueChange,
}: CliCommandSectionProps) {
  // Support both controlled and uncontrolled modes
  const [internalValue, setInternalValue] = useState<string>('basic');
  const selectedCommand = value ?? internalValue;
  const setSelectedCommand = onValueChange ?? setInternalValue;

  const { copied, copy } = useCliCopy();

  // Get the current command based on selection
  const currentCommand = getCommandForOption(artifactName, selectedCommand);

  // Handle copy button click
  const handleCopy = async () => {
    await copy(currentCommand);
  };

  return (
    <div className={cn('space-y-2', className)}>
      {/* Label - hidden when used in collapsible context */}
      {!hideLabel && (
        <label htmlFor="cli-command-select" className="text-sm font-medium text-foreground">
          CLI Deploy Command
        </label>
      )}

      {/* Command section: dropdown, code display, and copy button */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        {/* Select dropdown */}
        <Select value={selectedCommand} onValueChange={setSelectedCommand}>
          <SelectTrigger
            id="cli-command-select"
            className="w-full sm:w-[180px]"
            aria-label="Select command type"
          >
            <SelectValue placeholder="Select command" />
          </SelectTrigger>
          <SelectContent>
            {commandOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Code display */}
        <div className="flex min-w-0 flex-1 items-center gap-2">
          <code className="flex-1 overflow-x-auto rounded-md border border-input bg-muted/50 px-3 py-2 font-mono text-sm">
            {currentCommand}
          </code>

          {/* Copy button - hidden when handled externally */}
          {!hideCopyButton && (
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
          )}
        </div>
      </div>
    </div>
  );
}
