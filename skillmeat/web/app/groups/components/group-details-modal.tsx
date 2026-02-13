'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { History, Info, Package, Plus, X } from 'lucide-react';
import { useArtifact, useGroup, useGroupArtifacts, useToast, useUpdateGroup } from '@/hooks';
import type { Group } from '@/types/groups';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

interface GroupDetailsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  group: Group | null;
}

function ArtifactHistoryRow({ artifactId }: { artifactId: string }) {
  const { data: artifact } = useArtifact(artifactId);
  return <span className="font-medium">{artifact?.name ?? artifactId}</span>;
}

export function GroupDetailsModal({ open, onOpenChange, group }: GroupDetailsModalProps) {
  const { toast } = useToast();
  const updateGroup = useUpdateGroup();

  const groupId = group?.id;
  const { data: detailedGroup } = useGroup(groupId ?? undefined);
  const { data: artifacts = [], isLoading: isLoadingArtifacts } = useGroupArtifacts(groupId ?? undefined);

  const [newTag, setNewTag] = useState('');
  const [localTags, setLocalTags] = useState<string[]>([]);
  const [isTagSaving, setIsTagSaving] = useState(false);

  useEffect(() => {
    if (!detailedGroup) {
      setLocalTags(group?.tags ?? []);
      return;
    }
    setLocalTags(detailedGroup.tags ?? []);
  }, [group?.tags, detailedGroup]);

  const sortedHistory = useMemo(() => {
    return [...artifacts].sort(
      (a, b) => new Date(b.added_at).getTime() - new Date(a.added_at).getTime()
    );
  }, [artifacts]);

  const persistTags = async (nextTags: string[]) => {
    if (!group) {
      return;
    }
    setIsTagSaving(true);
    try {
      await updateGroup.mutateAsync({
        id: group.id,
        data: { tags: nextTags },
      });
      setLocalTags(nextTags);
    } catch (error) {
      toast({
        title: 'Tag update failed',
        description: error instanceof Error ? error.message : 'Unexpected error.',
        variant: 'destructive',
      });
    } finally {
      setIsTagSaving(false);
    }
  };

  const handleAddTag = async () => {
    const tag = newTag.trim().toLowerCase();
    if (!tag) {
      return;
    }
    if (!/^[a-z0-9_-]{1,32}$/.test(tag)) {
      toast({
        title: 'Invalid tag',
        description: 'Use 1-32 characters from [a-z0-9_-].',
        variant: 'destructive',
      });
      return;
    }
    if (localTags.includes(tag)) {
      setNewTag('');
      return;
    }
    const nextTags = [...localTags, tag].slice(0, 20);
    await persistTags(nextTags);
    setNewTag('');
  };

  const handleRemoveTag = async (tag: string) => {
    const nextTags = localTags.filter((value) => value !== tag);
    await persistTags(nextTags);
  };

  if (!group) {
    return null;
  }

  const displayGroup = detailedGroup ?? group;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[85vh] max-w-4xl flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>{displayGroup.name}</DialogTitle>
          <DialogDescription>
            Group details, artifacts, and change history.
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="overview" className="flex min-h-0 flex-1 flex-col">
          <TabsList className="w-full justify-start">
            <TabsTrigger value="overview">
              <Info className="mr-1 h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="artifacts">
              <Package className="mr-1 h-4 w-4" />
              Artifacts
            </TabsTrigger>
            <TabsTrigger value="history">
              <History className="mr-1 h-4 w-4" />
              History
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="min-h-0 flex-1 overflow-y-auto">
            <div className="space-y-4 py-2">
              <div>
                <p className="text-sm font-medium">Description</p>
                <p className="text-sm text-muted-foreground">
                  {displayGroup.description || 'No description provided.'}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="font-medium">Color</p>
                  <p className="text-muted-foreground">{displayGroup.color ?? 'slate'}</p>
                </div>
                <div>
                  <p className="font-medium">Icon</p>
                  <p className="text-muted-foreground">{displayGroup.icon ?? 'layers'}</p>
                </div>
                <div>
                  <p className="font-medium">Artifacts</p>
                  <p className="text-muted-foreground">{displayGroup.artifact_count}</p>
                </div>
                <div>
                  <p className="font-medium">Updated</p>
                  <p className="text-muted-foreground">
                    {new Date(displayGroup.updated_at).toLocaleString()}
                  </p>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-sm font-medium">Tags</p>
                <div className="flex flex-wrap gap-2">
                  {localTags.length > 0 ? (
                    localTags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="gap-1">
                        {tag}
                        <button
                          type="button"
                          className="rounded p-0.5 hover:bg-black/10"
                          onClick={() => void handleRemoveTag(tag)}
                          disabled={isTagSaving}
                          aria-label={`Remove tag ${tag}`}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      </Badge>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground">No tags yet.</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <Input
                    value={newTag}
                    onChange={(event) => setNewTag(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        void handleAddTag();
                      }
                    }}
                    placeholder="Add tag"
                    disabled={isTagSaving}
                  />
                  <Button onClick={() => void handleAddTag()} disabled={isTagSaving}>
                    <Plus className="mr-1 h-4 w-4" />
                    Add Tag
                  </Button>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="artifacts" className="min-h-0 flex-1 overflow-y-auto">
            <div className="space-y-3 py-2">
              <div className="flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  {artifacts.length} artifact{artifacts.length === 1 ? '' : 's'} in this group
                </p>
                <Button asChild size="sm" variant="outline">
                  <Link href={`/collection?collection=${group.collection_id}&group=${group.id}`}>
                    Open in Collection
                  </Link>
                </Button>
              </div>
              {isLoadingArtifacts ? (
                <p className="text-sm text-muted-foreground">Loading artifacts...</p>
              ) : artifacts.length === 0 ? (
                <p className="text-sm text-muted-foreground">No artifacts in this group.</p>
              ) : (
                <div className="space-y-2">
                  {artifacts.map((artifact) => (
                    <div
                      key={artifact.artifact_id}
                      className="flex items-center justify-between rounded border px-3 py-2"
                    >
                      <ArtifactHistoryRow artifactId={artifact.artifact_id} />
                      <span className="text-xs text-muted-foreground">
                        Added {new Date(artifact.added_at).toLocaleDateString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="history" className="min-h-0 flex-1 overflow-y-auto">
            <div className="space-y-3 py-2">
              <p className="text-sm text-muted-foreground">
                Showing artifact additions from group membership data. Removal events are not yet
                persisted by the API.
              </p>
              {sortedHistory.length === 0 ? (
                <p className="text-sm text-muted-foreground">No group history yet.</p>
              ) : (
                <div className="space-y-2">
                  {sortedHistory.map((entry) => (
                    <div
                      key={`${entry.artifact_id}-${entry.added_at}`}
                      className="flex items-center justify-between rounded border px-3 py-2"
                    >
                      <div className="text-sm">
                        <ArtifactHistoryRow artifactId={entry.artifact_id} /> added to group
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {new Date(entry.added_at).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
