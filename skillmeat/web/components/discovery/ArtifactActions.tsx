'use client';

import { useState } from 'react';
import { Download, EyeOff, Eye, Info, Copy, MoreHorizontal } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useToastNotification } from '@/hooks';
import type { DiscoveredArtifact } from '@/types/discovery';

/**
 * Props for ArtifactActions component
 */
export interface ArtifactActionsProps {
  /**
   * The artifact to show actions for
   */
  artifact: DiscoveredArtifact;

  /**
   * Whether this artifact is currently in skip preferences
   */
  isSkipped: boolean;

  /**
   * Callback when Import action is clicked
   */
  onImport: () => void;

  /**
   * Callback when Skip/Un-skip action is clicked
   */
  onToggleSkip: (skip: boolean) => void;

  /**
   * Callback when View Details action is clicked
   */
  onViewDetails: () => void;

  /**
   * Whether the artifact is already imported (disables import action)
   */
  isImported?: boolean;
}

/**
 * ArtifactActions Component
 *
 * Provides a dropdown menu with actions for discovered artifacts.
 * Supports import, skip/un-skip, view details, and copy source URL.
 *
 * Accessibility:
 * - Keyboard navigation: Tab to trigger, Enter to open, Arrow keys to navigate
 * - Screen reader support: Descriptive aria-labels for all actions
 * - Visual feedback: Icons and labels for all actions
 *
 * @example
 * ```tsx
 * <ArtifactActions
 *   artifact={artifact}
 *   isSkipped={false}
 *   isImported={false}
 *   onImport={() => handleImport(artifact)}
 *   onToggleSkip={(skip) => handleToggleSkip(artifact, skip)}
 *   onViewDetails={() => handleViewDetails(artifact)}
 * />
 * ```
 */
export function ArtifactActions({
  artifact,
  isSkipped,
  onImport,
  onToggleSkip,
  onViewDetails,
  isImported = false,
}: ArtifactActionsProps) {
  const { showSuccess } = useToastNotification();
  const [open, setOpen] = useState(false);

  /**
   * Handle copying source URL to clipboard
   */
  const handleCopySource = async () => {
    if (!artifact.source) {
      return;
    }

    try {
      await navigator.clipboard.writeText(artifact.source);
      showSuccess('Source URL copied to clipboard');
      setOpen(false);
    } catch (error) {
      // Fallback for browsers that don't support clipboard API
      console.error('Failed to copy to clipboard:', error);
      // Try fallback method
      try {
        const textArea = document.createElement('textarea');
        textArea.value = artifact.source;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showSuccess('Source URL copied to clipboard');
        setOpen(false);
      } catch (fallbackError) {
        console.error('Fallback copy also failed:', fallbackError);
      }
    }
  };

  /**
   * Handle import action
   */
  const handleImport = () => {
    onImport();
    setOpen(false);
  };

  /**
   * Handle toggle skip action
   */
  const handleToggleSkip = () => {
    onToggleSkip(!isSkipped);
    setOpen(false);
  };

  /**
   * Handle view details action
   */
  const handleViewDetails = () => {
    onViewDetails();
    setOpen(false);
  };

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Actions for ${artifact.name}`}
          className="h-8 w-8"
        >
          <MoreHorizontal className="h-4 w-4" aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {/* Import Action */}
        <DropdownMenuItem
          onClick={handleImport}
          disabled={isImported}
          aria-label={isImported ? 'Already imported' : 'Import to Collection'}
          className="cursor-pointer"
        >
          <Download className="mr-2 h-4 w-4" aria-hidden="true" />
          <span>{isImported ? 'Already imported' : 'Import to Collection'}</span>
        </DropdownMenuItem>

        {/* Skip/Un-skip Action */}
        <DropdownMenuItem onClick={handleToggleSkip} className="cursor-pointer">
          {isSkipped ? (
            <>
              <Eye className="mr-2 h-4 w-4" aria-hidden="true" />
              <span>Un-skip</span>
            </>
          ) : (
            <>
              <EyeOff className="mr-2 h-4 w-4" aria-hidden="true" />
              <span>Skip for future</span>
            </>
          )}
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        {/* View Details Action */}
        <DropdownMenuItem onClick={handleViewDetails} className="cursor-pointer">
          <Info className="mr-2 h-4 w-4" aria-hidden="true" />
          <span>View Details</span>
        </DropdownMenuItem>

        {/* Copy Source URL Action */}
        <DropdownMenuItem
          onClick={handleCopySource}
          disabled={!artifact.source}
          className="cursor-pointer"
          aria-label="Copy Source URL"
        >
          <Copy className="mr-2 h-4 w-4" aria-hidden="true" />
          <span>Copy Source URL</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
