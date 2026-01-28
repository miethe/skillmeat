'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
import { cn } from '@/lib/utils';
import { X, Link as LinkIcon, AlertCircle, Plus, RefreshCw, Loader2 } from 'lucide-react';
import type { LinkType } from './artifact-linking-dialog';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

/**
 * Reference to a linked artifact
 */
export interface LinkedArtifactReference {
  artifact_id?: string;
  artifact_name: string;
  artifact_type: string;
  source_name?: string;
  link_type: LinkType;
  created_at?: string;
}

// Re-export LinkType for convenience
export type { LinkType };

export interface LinkedArtifactsSectionProps {
  /** ID of the source artifact */
  artifactId: string;
  /** Array of linked artifacts */
  linkedArtifacts?: LinkedArtifactReference[];
  /** Array of reference strings that couldn't be resolved to artifacts */
  unlinkedReferences?: string[];
  /** Callback when a link is successfully created */
  onLinkCreated?: () => void;
  /** Callback when a link is successfully deleted */
  onLinkDeleted?: () => void;
  /** Callback to open the artifact linking dialog */
  onAddLinkClick?: () => void;
  /** Whether the section is in a loading state */
  isLoading?: boolean;
  /** Error message to display */
  error?: string | null;
  /** Callback to retry loading */
  onRetry?: () => void;
}

/**
 * Get badge styling based on link type
 */
function getLinkTypeBadgeProps(linkType: LinkType): {
  variant: 'default' | 'outline' | 'secondary';
  className: string;
} {
  switch (linkType) {
    case 'requires':
      return { variant: 'default', className: '' };
    case 'enables':
      return { variant: 'outline', className: '' };
    case 'related':
      return { variant: 'secondary', className: 'border-dashed' };
    default:
      return { variant: 'secondary', className: '' };
  }
}

/**
 * Get readable label for link type
 */
function getLinkTypeLabel(linkType: LinkType): string {
  switch (linkType) {
    case 'requires':
      return 'Requires';
    case 'enables':
      return 'Enables';
    case 'related':
      return 'Related';
    default:
      return linkType;
  }
}

/**
 * Delete a linked artifact
 */
async function deleteLinkedArtifact(
  artifactId: string,
  targetArtifactId: string
): Promise<void> {
  const response = await fetch(
    buildUrl(`/artifacts/${encodeURIComponent(artifactId)}/linked-artifacts/${encodeURIComponent(targetArtifactId)}`),
    {
      method: 'DELETE',
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to delete link' }));
    throw new Error(error.detail || 'Failed to delete link');
  }
}

/**
 * LinkedArtifactsSection - Display and manage linked artifacts for an artifact
 *
 * Shows a grid of linked artifacts with their type and relationship,
 * allows deletion of links, and displays unlinked references that
 * couldn't be resolved.
 *
 * @example
 * ```tsx
 * <LinkedArtifactsSection
 *   artifactId="abc123"
 *   linkedArtifacts={[
 *     { artifact_id: 'def456', artifact_name: 'python-utils', artifact_type: 'skill', link_type: 'requires' }
 *   ]}
 *   unlinkedReferences={['unknown-tool']}
 *   onLinkDeleted={() => refetch()}
 *   onAddLinkClick={() => setShowDialog(true)}
 * />
 * ```
 */
export function LinkedArtifactsSection({
  artifactId,
  linkedArtifacts = [],
  unlinkedReferences = [],
  onLinkCreated: _onLinkCreated,
  onLinkDeleted,
  onAddLinkClick,
  isLoading = false,
  error = null,
  onRetry,
}: LinkedArtifactsSectionProps) {
  // Note: _onLinkCreated is reserved for future use when adding in-component link creation
  void _onLinkCreated;
  const queryClient = useQueryClient();
  const [deleteTarget, setDeleteTarget] = useState<LinkedArtifactReference | null>(null);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: ({ targetArtifactId }: { targetArtifactId: string }) =>
      deleteLinkedArtifact(artifactId, targetArtifactId),
    onSuccess: () => {
      // Invalidate artifact queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ['artifact', artifactId] });
      queryClient.invalidateQueries({ queryKey: ['artifacts'] });
      onLinkDeleted?.();
      setShowDeleteDialog(false);
      setDeleteTarget(null);
    },
  });

  const handleDeleteClick = (artifact: LinkedArtifactReference) => {
    setDeleteTarget(artifact);
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = () => {
    if (deleteTarget?.artifact_id) {
      deleteMutation.mutate({ targetArtifactId: deleteTarget.artifact_id });
    }
  };

  const handleCancelDelete = () => {
    if (!deleteMutation.isPending) {
      setShowDeleteDialog(false);
      setDeleteTarget(null);
    }
  };

  const hasLinkedArtifacts = linkedArtifacts.length > 0;
  const hasUnlinkedReferences = unlinkedReferences.length > 0;
  const isEmpty = !hasLinkedArtifacts && !hasUnlinkedReferences;

  // Error state
  if (error) {
    return (
      <section aria-labelledby="linked-artifacts-heading" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 id="linked-artifacts-heading" className="text-lg font-semibold">
            Linked Artifacts
          </h2>
        </div>
        <Card className="border-destructive">
          <CardContent className="flex flex-col items-center justify-center gap-4 py-8">
            <AlertCircle className="h-8 w-8 text-destructive" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">{error}</p>
            {onRetry && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRetry}
                aria-label="Retry loading linked artifacts"
              >
                <RefreshCw className="mr-2 h-4 w-4" aria-hidden="true" />
                Retry
              </Button>
            )}
          </CardContent>
        </Card>
      </section>
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <section aria-labelledby="linked-artifacts-heading" className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 id="linked-artifacts-heading" className="text-lg font-semibold">
            Linked Artifacts
          </h2>
        </div>
        <div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          aria-busy="true"
          aria-label="Loading linked artifacts"
        >
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="space-y-3">
                  <div className="h-4 w-3/4 rounded bg-muted" />
                  <div className="flex gap-2">
                    <div className="h-5 w-16 rounded bg-muted" />
                    <div className="h-5 w-16 rounded bg-muted" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section aria-labelledby="linked-artifacts-heading" className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 id="linked-artifacts-heading" className="text-lg font-semibold">
          Linked Artifacts
          {hasLinkedArtifacts && (
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              ({linkedArtifacts.length})
            </span>
          )}
        </h2>
        {onAddLinkClick && (
          <Button
            variant="outline"
            size="sm"
            onClick={onAddLinkClick}
            aria-label="Add artifact link"
          >
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            Add Link
          </Button>
        )}
      </div>

      {/* Empty state */}
      {isEmpty && (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-4 py-8">
            <LinkIcon className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
            <div className="text-center">
              <p className="text-sm font-medium">No linked artifacts</p>
              <p className="text-sm text-muted-foreground">
                This artifact has no dependencies or relationships with other artifacts.
              </p>
            </div>
            {onAddLinkClick && (
              <Button variant="outline" size="sm" onClick={onAddLinkClick}>
                <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
                Add First Link
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {/* Linked artifacts grid */}
      {hasLinkedArtifacts && (
        <div
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
          role="list"
          aria-label="Linked artifacts"
        >
          {linkedArtifacts.map((artifact, index) => {
            const badgeProps = getLinkTypeBadgeProps(artifact.link_type);
            const uniqueKey = artifact.artifact_id || `${artifact.artifact_name}-${index}`;

            return (
              <Card
                key={uniqueKey}
                className="group relative transition-shadow hover:shadow-md"
                role="listitem"
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1 space-y-2">
                      {/* Artifact name - clickable if has ID */}
                      {artifact.artifact_id ? (
                        <Link
                          href={`/artifacts/${artifact.artifact_id}`}
                          className="block truncate font-medium text-foreground hover:text-primary hover:underline focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                          aria-label={`View ${artifact.artifact_name} artifact`}
                        >
                          {artifact.artifact_name}
                        </Link>
                      ) : (
                        <span className="block truncate font-medium text-muted-foreground">
                          {artifact.artifact_name}
                        </span>
                      )}

                      {/* Badges */}
                      <div className="flex flex-wrap gap-1.5">
                        <Badge variant="secondary" className="text-xs">
                          {artifact.artifact_type}
                        </Badge>
                        <Badge
                          variant={badgeProps.variant}
                          className={cn('text-xs', badgeProps.className)}
                        >
                          {getLinkTypeLabel(artifact.link_type)}
                        </Badge>
                      </div>
                    </div>

                    {/* Delete button */}
                    {artifact.artifact_id && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
                        onClick={() => handleDeleteClick(artifact)}
                        aria-label={`Remove link to ${artifact.artifact_name}`}
                        disabled={deleteMutation.isPending}
                      >
                        <X className="h-4 w-4" aria-hidden="true" />
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Unlinked references section */}
      {hasUnlinkedReferences && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-amber-500" aria-hidden="true" />
            <h3 className="text-sm font-medium">Unresolved References</h3>
            <span className="text-xs text-muted-foreground">({unlinkedReferences.length})</span>
          </div>
          <p className="text-xs text-muted-foreground">
            These references were found but could not be matched to artifacts in your collection.
          </p>
          <div
            className="flex flex-wrap gap-2"
            role="list"
            aria-label="Unresolved artifact references"
          >
            {unlinkedReferences.map((reference, index) => (
              <Badge
                key={`${reference}-${index}`}
                variant="outline"
                className="border-amber-500/50 text-amber-700 dark:text-amber-400"
                role="listitem"
              >
                {reference}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Delete confirmation dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={handleCancelDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove Artifact Link</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to remove the link to{' '}
              <span className="font-medium">{deleteTarget?.artifact_name}</span>? This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                  Removing...
                </>
              ) : (
                'Remove Link'
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </section>
  );
}
