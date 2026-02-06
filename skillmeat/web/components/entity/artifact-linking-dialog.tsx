'use client';

import { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { Search, Loader2, AlertCircle, Link as LinkIcon } from 'lucide-react';
import { useDebounce } from '@/hooks';
import type { ArtifactType } from '@/types/artifact';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';
const API_VERSION = process.env.NEXT_PUBLIC_API_VERSION || 'v1';

function buildUrl(path: string): string {
  return `${API_BASE}/api/${API_VERSION}${path}`;
}

export type LinkType = 'requires' | 'enables' | 'related';

interface SearchArtifact {
  id: string;
  name: string;
  type: ArtifactType;
  source?: string;
  metadata?: {
    description?: string;
  };
}

interface SearchResponse {
  items: SearchArtifact[];
  page_info: {
    total_count: number;
  };
}

interface ArtifactLinkingDialogProps {
  /** Source artifact being linked FROM */
  artifactId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
}

/**
 * ArtifactLinkingDialog - Modal dialog for searching and linking artifacts
 *
 * Allows users to search for existing artifacts and create links between them.
 * Supports filtering by artifact type and selecting the relationship type.
 *
 * Features:
 * - Debounced search input (300ms)
 * - Type filter dropdown
 * - Single-select mode with radio buttons
 * - Link type selector (requires, enables, related)
 * - Loading and error states
 * - Keyboard navigation support
 *
 * @example
 * ```tsx
 * <ArtifactLinkingDialog
 *   artifactId={currentArtifact.id}
 *   open={showLinkDialog}
 *   onOpenChange={setShowLinkDialog}
 *   onSuccess={() => refetchLinks()}
 * />
 * ```
 */
export function ArtifactLinkingDialog({
  artifactId,
  open,
  onOpenChange,
  onSuccess,
}: ArtifactLinkingDialogProps) {
  const queryClient = useQueryClient();

  // Form state
  const [searchQuery, setSearchQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<ArtifactType | 'all'>('all');
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [linkType, setLinkType] = useState<LinkType>('related');
  const [error, setError] = useState<string | null>(null);

  // Debounced search query
  const debouncedSearch = useDebounce(searchQuery, 300);

  // Reset form state when dialog opens/closes
  useEffect(() => {
    if (open) {
      setSearchQuery('');
      setTypeFilter('all');
      setSelectedArtifactId(null);
      setLinkType('related');
      setError(null);
    }
  }, [open]);

  // Search artifacts query
  const {
    data: searchResults,
    isLoading: isSearching,
    error: searchError,
  } = useQuery<SearchResponse>({
    queryKey: ['artifact-search', debouncedSearch, typeFilter, artifactId],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (debouncedSearch) params.set('search', debouncedSearch);
      if (typeFilter !== 'all') params.set('artifact_type', typeFilter);
      params.set('exclude_id', artifactId);
      params.set('limit', '20');

      const queryString = params.toString();
      const response = await fetch(buildUrl(`/artifacts?${queryString}`));

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.detail || 'Failed to search artifacts');
      }

      return response.json();
    },
    enabled: open && debouncedSearch.length > 0,
    staleTime: 30000, // Cache search results for 30 seconds
  });

  // Create link mutation
  const createLinkMutation = useMutation({
    mutationFn: async ({
      targetArtifactId,
      linkType,
    }: {
      targetArtifactId: string;
      linkType: LinkType;
    }) => {
      const response = await fetch(
        buildUrl(`/artifacts/${encodeURIComponent(artifactId)}/linked-artifacts`),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            target_artifact_id: targetArtifactId,
            link_type: linkType,
          }),
        }
      );

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.detail || 'Failed to create artifact link');
      }

      return response.json();
    },
    onSuccess: () => {
      // Invalidate relevant queries
      queryClient.invalidateQueries({ queryKey: ['artifact', artifactId] });
      queryClient.invalidateQueries({ queryKey: ['linked-artifacts', artifactId] });

      // Close dialog and notify parent
      onOpenChange(false);
      onSuccess?.();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const handleCreateLink = useCallback(() => {
    if (!selectedArtifactId) {
      setError('Please select an artifact to link');
      return;
    }

    setError(null);
    createLinkMutation.mutate({
      targetArtifactId: selectedArtifactId,
      linkType,
    });
  }, [selectedArtifactId, linkType, createLinkMutation]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && selectedArtifactId && !createLinkMutation.isPending) {
      e.preventDefault();
      handleCreateLink();
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!createLinkMutation.isPending) {
      onOpenChange(newOpen);
    }
  };

  // Filter out the current artifact from results (extra safety in case backend doesn't support exclude_id)
  const filteredResults =
    searchResults?.items?.filter((artifact) => artifact.id !== artifactId) || [];

  const isLoading = createLinkMutation.isPending;
  const displayError = error || (searchError instanceof Error ? searchError.message : null);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-lg" onKeyDown={handleKeyDown}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <LinkIcon className="h-5 w-5" />
            Link Artifact
          </DialogTitle>
          <DialogDescription>
            Search for an artifact to link. Choose the relationship type to describe how the
            artifacts are connected.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Search Input */}
          <div className="space-y-2">
            <Label htmlFor="artifact-search">Search Artifacts</Label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="artifact-search"
                placeholder="Type to search artifacts..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value);
                  setError(null);
                }}
                className="pl-9"
                disabled={isLoading}
                autoFocus
              />
            </div>
          </div>

          {/* Type Filter */}
          <div className="space-y-2">
            <Label htmlFor="type-filter">Filter by Type</Label>
            <Select
              value={typeFilter}
              onValueChange={(value) => setTypeFilter(value as ArtifactType | 'all')}
              disabled={isLoading}
            >
              <SelectTrigger id="type-filter">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                <SelectItem value="skill">Skills</SelectItem>
                <SelectItem value="command">Commands</SelectItem>
                <SelectItem value="agent">Agents</SelectItem>
                <SelectItem value="mcp">MCP Servers</SelectItem>
                <SelectItem value="hook">Hooks</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Search Results */}
          <div className="space-y-2">
            <Label>Select Artifact</Label>
            <div className="max-h-48 overflow-y-auto rounded-md border">
              {!debouncedSearch ? (
                <div className="flex items-center justify-center p-4 text-sm text-muted-foreground">
                  Type to search for artifacts
                </div>
              ) : isSearching ? (
                <div className="flex items-center justify-center p-4">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="ml-2 text-sm text-muted-foreground">Searching...</span>
                </div>
              ) : filteredResults.length === 0 ? (
                <div className="flex items-center justify-center p-4 text-sm text-muted-foreground">
                  No artifacts found
                </div>
              ) : (
                <RadioGroup
                  value={selectedArtifactId || ''}
                  onValueChange={setSelectedArtifactId}
                  className="p-2"
                >
                  {filteredResults.map((artifact) => (
                    <div
                      key={artifact.id}
                      className={cn(
                        'flex items-start space-x-3 rounded-md p-2 transition-colors',
                        'hover:bg-accent',
                        selectedArtifactId === artifact.id && 'bg-accent'
                      )}
                    >
                      <RadioGroupItem
                        value={artifact.id}
                        id={`artifact-${artifact.id}`}
                        className="mt-1"
                        disabled={isLoading}
                      />
                      <Label
                        htmlFor={`artifact-${artifact.id}`}
                        className="flex-1 cursor-pointer font-normal"
                      >
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{artifact.name}</span>
                          <Badge variant="outline" className="text-xs">
                            {artifact.type}
                          </Badge>
                        </div>
                        {artifact.source && (
                          <div className="mt-1 truncate text-xs text-muted-foreground">
                            {artifact.source}
                          </div>
                        )}
                      </Label>
                    </div>
                  ))}
                </RadioGroup>
              )}
            </div>
            {searchResults?.page_info?.total_count && searchResults.page_info.total_count > 20 && (
              <p className="text-xs text-muted-foreground">
                Showing 20 of {searchResults.page_info.total_count} results. Refine your search for
                more specific results.
              </p>
            )}
          </div>

          {/* Link Type Selector */}
          <div className="space-y-2">
            <Label htmlFor="link-type">Relationship Type</Label>
            <Select
              value={linkType}
              onValueChange={(value) => setLinkType(value as LinkType)}
              disabled={isLoading}
            >
              <SelectTrigger id="link-type">
                <SelectValue placeholder="Select relationship" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="requires">
                  <div className="flex flex-col">
                    <span>Requires</span>
                    <span className="text-xs text-muted-foreground">
                      This artifact depends on the linked artifact
                    </span>
                  </div>
                </SelectItem>
                <SelectItem value="enables">
                  <div className="flex flex-col">
                    <span>Enables</span>
                    <span className="text-xs text-muted-foreground">
                      This artifact unlocks or enhances the linked artifact
                    </span>
                  </div>
                </SelectItem>
                <SelectItem value="related">
                  <div className="flex flex-col">
                    <span>Related</span>
                    <span className="text-xs text-muted-foreground">
                      Artifacts are related but not dependent
                    </span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Error Display */}
          {displayError && (
            <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-600 dark:border-red-900 dark:bg-red-950 dark:text-red-400">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{displayError}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={handleCreateLink} disabled={isLoading || !selectedArtifactId}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Link...
              </>
            ) : (
              'Create Link'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
