'use client';

import { useState } from 'react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp, X, Trash2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { parseArtifactKey } from '@/lib/skip-preferences';
import { useTrackDiscovery } from '@/lib/analytics';
import type { SkipPreference } from '@/types/discovery';

export interface SkipPreferencesListProps {
  skipPrefs: SkipPreference[];
  projectId?: string;
  onRemoveSkip: (artifactKey: string) => void;
  onClearAll: () => void;
  isLoading?: boolean;
}

/**
 * SkipPreferencesList - Displays and manages artifacts marked to skip
 *
 * Shows a collapsible list of skipped artifacts with options to:
 * - Un-skip individual artifacts
 * - Clear all skips with confirmation dialog
 *
 * Features:
 * - Collapsible accordion with count badge
 * - Per-artifact type badge and skip reason
 * - Confirmation dialog for bulk clear
 * - Empty state when no skips
 * - Full keyboard navigation and ARIA support
 *
 * @example
 * ```tsx
 * <SkipPreferencesList
 *   skipPrefs={skipPreferences}
 *   projectId="project-123"
 *   onRemoveSkip={(key) => removeSkipPref(projectId, key)}
 *   onClearAll={() => clearSkipPrefs(projectId)}
 * />
 * ```
 */
export function SkipPreferencesList({
  skipPrefs,
  projectId = 'unknown',
  onRemoveSkip,
  onClearAll,
  isLoading = false,
}: SkipPreferencesListProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showClearDialog, setShowClearDialog] = useState(false);

  const tracking = useTrackDiscovery();
  const count = skipPrefs.length;
  const isEmpty = count === 0;

  // Auto-collapse when empty
  const shouldBeOpen = isOpen && !isEmpty;

  const handleRemoveSkip = (artifactKey: string) => {
    tracking.trackSkipToggle(artifactKey, false);
    onRemoveSkip(artifactKey);
  };

  const handleClearAll = () => {
    tracking.trackSkipCleared(projectId, count);
    onClearAll();
    setShowClearDialog(false);
  };

  return (
    <>
      <Collapsible
        open={shouldBeOpen}
        onOpenChange={setIsOpen}
        className="border rounded-lg bg-card"
      >
        <CollapsibleTrigger asChild>
          <button
            className={cn(
              'flex w-full items-center justify-between p-4 hover:bg-accent transition-colors',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2'
            )}
            aria-expanded={shouldBeOpen}
            aria-controls="skip-preferences-content"
          >
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">Skipped Artifacts</h3>
              {count > 0 && (
                <Badge variant="secondary" className="ml-2">
                  {count}
                </Badge>
              )}
            </div>
            {shouldBeOpen ? (
              <ChevronUp className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            ) : (
              <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            )}
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent id="skip-preferences-content" className="px-4 pb-4">
          {isEmpty ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No artifacts are currently skipped.
            </div>
          ) : (
            <div className="space-y-3">
              <div className="space-y-2">
                {skipPrefs.map((pref) => {
                  const parsed = parseArtifactKey(pref.artifact_key);
                  const displayName = parsed ? parsed.name : pref.artifact_key;
                  const artifactType = parsed ? parsed.type : 'unknown';

                  return (
                    <div
                      key={pref.artifact_key}
                      className="flex items-start gap-3 p-3 rounded-md border bg-background"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-medium text-sm truncate">
                            {displayName}
                          </span>
                          <Badge variant="outline" className="text-xs">
                            {artifactType}
                          </Badge>
                        </div>
                        {pref.skip_reason && (
                          <p className="text-xs text-muted-foreground line-clamp-2">
                            {pref.skip_reason}
                          </p>
                        )}
                        <p className="text-xs text-muted-foreground mt-1">
                          Skipped {new Date(pref.added_date).toLocaleDateString()}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRemoveSkip(pref.artifact_key)}
                        disabled={isLoading}
                        aria-label={`Un-skip ${displayName}`}
                        className="shrink-0"
                      >
                        <X className="h-4 w-4" />
                        <span className="ml-1">Un-skip</span>
                      </Button>
                    </div>
                  );
                })}
              </div>

              {count > 1 && (
                <div className="pt-2 border-t">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setShowClearDialog(true)}
                    disabled={isLoading}
                    className="w-full"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Clear All Skips
                  </Button>
                </div>
              )}
            </div>
          )}
        </CollapsibleContent>
      </Collapsible>

      {/* Confirmation Dialog for Clear All */}
      <AlertDialog open={showClearDialog} onOpenChange={setShowClearDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clear all skip preferences?</AlertDialogTitle>
            <AlertDialogDescription>
              This will clear all {count} skipped artifact{count !== 1 ? 's' : ''}. These
              artifacts will appear in future discovery scans and can be imported.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleClearAll}
              className={cn('bg-destructive text-destructive-foreground hover:bg-destructive/90')}
            >
              Clear All
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
