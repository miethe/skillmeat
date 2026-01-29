'use client';

/**
 * Bundle Preview Component
 *
 * Shows what will be imported before committing to the import
 */

import {
  Package,
  AlertTriangle,
  CheckCircle,
  XCircle,
  GitMerge,
  GitBranch,
  FileWarning,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { BundlePreview as BundlePreviewType } from '@/types/bundle';

export interface BundlePreviewProps {
  preview: BundlePreviewType;
  className?: string;
}

export function BundlePreview({ preview, className }: BundlePreviewProps) {
  const hasConflicts = preview.conflicts.length > 0;

  return (
    <div className={className}>
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Package className="h-5 w-5" />
            <CardTitle>{preview.bundle.metadata.name}</CardTitle>
          </div>
          {preview.bundle.metadata.description && (
            <p className="mt-2 text-sm text-muted-foreground">
              {preview.bundle.metadata.description}
            </p>
          )}
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Bundle Info */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Artifacts</p>
              <p className="font-medium">{preview.bundle.artifacts.length}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Size</p>
              <p className="font-medium">{(preview.bundle.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
            <div>
              <p className="text-muted-foreground">Format</p>
              <p className="font-medium uppercase">{preview.bundle.format}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Exported</p>
              <p className="font-medium">
                {new Date(preview.bundle.exportedAt).toLocaleDateString()}
              </p>
            </div>
          </div>

          {/* Tags */}
          {preview.bundle.metadata.tags && preview.bundle.metadata.tags.length > 0 && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">Tags</p>
              <div className="flex flex-wrap gap-1">
                {preview.bundle.metadata.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Import Summary */}
          <div className="space-y-2 border-t pt-2">
            <p className="text-sm font-medium">Import Summary</p>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {preview.willImport > 0 && (
                <div className="flex items-center gap-2 text-green-600">
                  <CheckCircle className="h-4 w-4" />
                  <span>
                    {preview.willImport} new {preview.willImport === 1 ? 'artifact' : 'artifacts'}
                  </span>
                </div>
              )}
              {preview.willMerge > 0 && (
                <div className="flex items-center gap-2 text-blue-600">
                  <GitMerge className="h-4 w-4" />
                  <span>{preview.willMerge} to merge</span>
                </div>
              )}
              {preview.willFork > 0 && (
                <div className="flex items-center gap-2 text-purple-600">
                  <GitBranch className="h-4 w-4" />
                  <span>{preview.willFork} to fork</span>
                </div>
              )}
              {preview.willSkip > 0 && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <XCircle className="h-4 w-4" />
                  <span>{preview.willSkip} to skip</span>
                </div>
              )}
            </div>
          </div>

          {/* Conflicts Warning */}
          {hasConflicts && (
            <div className="rounded-lg border border-yellow-500/50 bg-yellow-500/10 p-3">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0 text-yellow-600" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-yellow-900 dark:text-yellow-100">
                    {preview.conflicts.length} Conflict{preview.conflicts.length > 1 ? 's' : ''}{' '}
                    Detected
                  </p>
                  <ul className="mt-2 space-y-1 text-xs text-yellow-800 dark:text-yellow-200">
                    {preview.conflicts.map((conflict) => (
                      <li key={conflict.artifactId} className="flex items-start gap-1">
                        <FileWarning className="mt-0.5 h-3 w-3 flex-shrink-0" />
                        <span>
                          <strong>{conflict.artifactName}</strong>: {conflict.existingVersion} →{' '}
                          {conflict.incomingVersion} ({conflict.conflictType})
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}

          {/* Artifact List */}
          <div className="space-y-2">
            <p className="text-sm font-medium">Included Artifacts</p>
            <div className="rounded-lg border">
              <div className="max-h-48 divide-y overflow-y-auto">
                {preview.bundle.artifacts.map((item) => {
                  const isNew = preview.newArtifacts.includes(item.artifact.id);
                  const isExisting = preview.existingArtifacts.includes(item.artifact.id);

                  return (
                    <div key={item.artifact.id} className="p-3 transition-colors hover:bg-muted/50">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            <p className="text-sm font-medium">{item.artifact.name}</p>
                            <Badge variant="outline" className="text-xs">
                              {item.artifact.type}
                            </Badge>
                          </div>
                          {item.artifact.description && (
                            <p className="mt-1 line-clamp-1 text-xs text-muted-foreground">
                              {item.artifact.description}
                            </p>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {isNew && (
                            <Badge variant="secondary" className="text-xs">
                              New
                            </Badge>
                          )}
                          {isExisting && (
                            <Badge variant="outline" className="text-xs">
                              Existing
                            </Badge>
                          )}
                          {item.artifact.version && (
                            <code className="rounded bg-muted px-2 py-1 text-xs">
                              {item.artifact.version}
                            </code>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
