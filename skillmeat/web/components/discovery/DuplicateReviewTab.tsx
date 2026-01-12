'use client';

import { useState, useMemo } from 'react';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  FileQuestion,
  ChevronRight,
  Link2,
  XCircle,
  AlertTriangle,
  Folder,
  FileText,
  Bot,
  Plug,
  Code,
  Package,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { DiscoveredArtifact, DuplicateDecisionAction } from '@/types/discovery';

export interface DuplicateReviewTabProps {
  artifacts: DiscoveredArtifact[];
  matchDecisions: Map<string, { collection_id: string; action: DuplicateDecisionAction }>;
  skippedPaths: Set<string>;
  onUpdateDecision: (
    path: string,
    collectionId: string | null,
    action: DuplicateDecisionAction
  ) => void;
}

/**
 * Map artifact types to Lucide icons
 */
const artifactTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  skill: Folder,
  command: FileText,
  agent: Bot,
  mcp: Plug,
  hook: Code,
};

/**
 * Get confidence badge color based on score
 */
function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.9) return 'bg-green-600';
  if (confidence >= 0.7) return 'bg-yellow-600';
  return 'bg-orange-600';
}

/**
 * Format confidence as percentage
 */
function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/**
 * DuplicateReviewTab Component
 *
 * Shows side-by-side comparison of discovered artifacts with their potential matches.
 * Left panel: List of artifacts with selection
 * Right panel: Selected artifact details + matched artifact info + action dropdown
 */
export function DuplicateReviewTab({
  artifacts,
  matchDecisions,
  skippedPaths,
  onUpdateDecision,
}: DuplicateReviewTabProps) {
  const [selectedPath, setSelectedPath] = useState<string | null>(
    artifacts.length > 0 ? (artifacts[0]?.path ?? null) : null
  );

  // Get selected artifact
  const selectedArtifact = useMemo(
    () => artifacts.find((a) => a.path === selectedPath) || null,
    [artifacts, selectedPath]
  );

  // Get current decision for selected artifact
  const currentDecision = selectedPath ? matchDecisions.get(selectedPath) : undefined;
  const isSkipped = selectedPath ? skippedPaths.has(selectedPath) : false;

  // Determine action value for dropdown
  const actionValue = useMemo(() => {
    if (isSkipped) return 'skip';
    if (currentDecision) return 'link';
    return 'not-duplicate';
  }, [isSkipped, currentDecision]);

  // Handle action change
  const handleActionChange = (value: string) => {
    if (!selectedPath || !selectedArtifact) return;

    const collectionId = selectedArtifact.collection_match?.matched_artifact_id || null;

    switch (value) {
      case 'link':
        if (collectionId) {
          onUpdateDecision(selectedPath, collectionId, 'link');
        }
        break;
      case 'skip':
        onUpdateDecision(selectedPath, null, 'skip');
        break;
      case 'not-duplicate':
        // This will remove from matches and add to newArtifacts in parent
        onUpdateDecision(selectedPath, null, 'link');
        break;
    }
  };

  if (artifacts.length === 0) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <div className="text-center">
          <FileQuestion className="mx-auto mb-4 h-12 w-12 text-muted-foreground/50" />
          <h3 className="mb-2 text-lg font-semibold">No Possible Duplicates</h3>
          <p className="text-sm text-muted-foreground">
            No artifacts require manual duplicate review.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0">
      {/* Left Panel: Artifact List */}
      <div className="w-1/3 min-w-[200px] border-r">
        <ScrollArea className="h-full">
          <div className="p-2">
            {artifacts.map((artifact) => {
              const decision = matchDecisions.get(artifact.path);
              const isSelected = artifact.path === selectedPath;
              const isArtifactSkipped = skippedPaths.has(artifact.path);
              const Icon = artifactTypeIcons[artifact.type] || Package;

              return (
                <button
                  key={artifact.path}
                  onClick={() => setSelectedPath(artifact.path)}
                  className={cn(
                    'flex w-full items-center gap-2 rounded-lg p-2 text-left transition-colors',
                    isSelected
                      ? 'bg-primary/10 border border-primary/30'
                      : 'hover:bg-muted/50',
                    isArtifactSkipped && 'opacity-50'
                  )}
                >
                  <Icon className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1">
                      <span className="truncate text-sm font-medium">{artifact.name}</span>
                    </div>
                    {artifact.collection_match && (
                      <div className="flex items-center gap-1 mt-0.5">
                        <Badge
                          variant="outline"
                          className={cn(
                            'text-[10px] px-1 py-0',
                            getConfidenceColor(artifact.collection_match.confidence),
                            'text-white border-0'
                          )}
                        >
                          {formatConfidence(artifact.collection_match.confidence)}
                        </Badge>
                        {decision?.action === 'link' && (
                          <Link2 className="h-3 w-3 text-blue-500" />
                        )}
                        {isArtifactSkipped && (
                          <XCircle className="h-3 w-3 text-gray-500" />
                        )}
                      </div>
                    )}
                  </div>
                  <ChevronRight className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                </button>
              );
            })}
          </div>
        </ScrollArea>
      </div>

      {/* Right Panel: Artifact Details */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          {selectedArtifact ? (
            <div className="space-y-4 p-4">
              {/* Warning Banner */}
              <div className="flex items-start gap-3 rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-900 dark:bg-yellow-950/20">
                <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0 text-yellow-600" />
                <div>
                  <p className="text-sm font-medium text-yellow-700 dark:text-yellow-500">
                    Possible Duplicate Detected
                  </p>
                  <p className="mt-1 text-xs text-yellow-600 dark:text-yellow-400">
                    This artifact has the same name and type as an existing collection item but different content.
                    Review the details and choose an action.
                  </p>
                </div>
              </div>

              {/* Discovered Artifact Card */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Package className="h-4 w-4 text-primary" />
                    Discovered Artifact
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-muted-foreground">Name:</span>
                      <p className="font-medium">{selectedArtifact.name}</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Type:</span>
                      <p>
                        <Badge variant="outline">{selectedArtifact.type}</Badge>
                      </p>
                    </div>
                    {selectedArtifact.version && (
                      <div>
                        <span className="text-muted-foreground">Version:</span>
                        <p className="font-mono text-xs">{selectedArtifact.version}</p>
                      </div>
                    )}
                    {selectedArtifact.source && (
                      <div>
                        <span className="text-muted-foreground">Source:</span>
                        <p className="font-mono text-xs truncate" title={selectedArtifact.source}>
                          {selectedArtifact.source}
                        </p>
                      </div>
                    )}
                  </div>
                  {selectedArtifact.description && (
                    <div>
                      <span className="text-sm text-muted-foreground">Description:</span>
                      <p className="mt-1 text-sm">{selectedArtifact.description}</p>
                    </div>
                  )}
                  <div>
                    <span className="text-sm text-muted-foreground">Path:</span>
                    <p className="mt-1 truncate font-mono text-xs text-muted-foreground" title={selectedArtifact.path}>
                      {selectedArtifact.path}
                    </p>
                  </div>
                  {selectedArtifact.content_hash && (
                    <div>
                      <span className="text-sm text-muted-foreground">Content Hash:</span>
                      <p className="mt-1 font-mono text-xs text-muted-foreground">
                        {selectedArtifact.content_hash.slice(0, 16)}...
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Matched Artifact Card */}
              {selectedArtifact.collection_match && selectedArtifact.collection_match.matched_artifact_id && (
                <Card className="border-blue-200 dark:border-blue-900">
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center justify-between text-base">
                      <div className="flex items-center gap-2">
                        <Link2 className="h-4 w-4 text-blue-500" />
                        Collection Match
                      </div>
                      <Badge
                        className={cn(
                          'text-xs',
                          getConfidenceColor(selectedArtifact.collection_match.confidence)
                        )}
                      >
                        {formatConfidence(selectedArtifact.collection_match.confidence)} confidence
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">Artifact ID:</span>
                        <p className="font-mono text-xs">
                          {selectedArtifact.collection_match.matched_artifact_id}
                        </p>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Name:</span>
                        <p className="font-medium">
                          {selectedArtifact.collection_match.matched_name}
                        </p>
                      </div>
                      <div className="col-span-2">
                        <span className="text-muted-foreground">Match Type:</span>
                        <p>
                          <Badge variant="outline" className="capitalize">
                            {selectedArtifact.collection_match.type.replace('_', ' ')}
                          </Badge>
                        </p>
                      </div>
                    </div>
                    <div className="rounded-md bg-muted/50 p-2 text-xs text-muted-foreground">
                      <strong>Name + Type match</strong>: Same name and artifact type, but the content differs.
                      This could be a modified version or an unrelated artifact with the same name.
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Action Selector */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Choose Action</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Select value={actionValue} onValueChange={handleActionChange}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select action..." />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="link">
                        <div className="flex items-center gap-2">
                          <Link2 className="h-4 w-4 text-blue-500" />
                          <span>Link to collection artifact</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="not-duplicate">
                        <div className="flex items-center gap-2">
                          <Package className="h-4 w-4 text-green-500" />
                          <span>Not a duplicate - import as new</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="skip">
                        <div className="flex items-center gap-2">
                          <XCircle className="h-4 w-4 text-gray-500" />
                          <span>Skip this artifact</span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>

                  {/* Action explanation */}
                  <div className="rounded-md bg-muted/50 p-2 text-xs text-muted-foreground">
                    {actionValue === 'link' && (
                      <>
                        <strong>Link:</strong> This artifact will be associated with the existing
                        collection artifact. No new artifact will be created.
                      </>
                    )}
                    {actionValue === 'not-duplicate' && (
                      <>
                        <strong>Import as new:</strong> This artifact will be imported as a new
                        artifact in your collection, separate from the matched one.
                      </>
                    )}
                    {actionValue === 'skip' && (
                      <>
                        <strong>Skip:</strong> This artifact will be ignored and not processed.
                      </>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <div className="flex h-full items-center justify-center p-8">
              <p className="text-muted-foreground">Select an artifact to review</p>
            </div>
          )}
        </ScrollArea>
      </div>
    </div>
  );
}
