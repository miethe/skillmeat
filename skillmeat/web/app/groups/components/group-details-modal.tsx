'use client';

import { useEffect, useMemo, useState, type ComponentType } from 'react';
import Link from 'next/link';
import * as LucideIcons from 'lucide-react';
import { ArrowUpRight, History, Info, Package } from 'lucide-react';
import { useArtifact, useGroup, useGroupArtifacts, useToast, useUpdateGroup } from '@/hooks';
import type { Group } from '@/types/groups';
import { ARTIFACT_TYPES, type ArtifactType } from '@/types/artifact';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  GroupMetadataEditor,
  type GroupColor,
  type GroupIcon,
  sanitizeGroupTags,
} from './group-metadata-editor';

interface GroupDetailsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  group: Group | null;
}

function inferArtifactType(
  artifactType: string | undefined,
  artifactId: string
): ArtifactType | null {
  if (artifactType && artifactType in ARTIFACT_TYPES) {
    return artifactType as ArtifactType;
  }

  const [prefix] = artifactId.split(':');
  if (prefix && prefix in ARTIFACT_TYPES) {
    return prefix as ArtifactType;
  }

  return null;
}

function getArtifactTypePresentation(type: ArtifactType | null): {
  label: string;
  Icon: ComponentType<{ className?: string }>;
} {
  if (!type) {
    return { label: 'Artifact', Icon: LucideIcons.Package };
  }

  const config = ARTIFACT_TYPES[type];
  const Icon =
    (LucideIcons as unknown as Record<string, ComponentType<{ className?: string }>>)[
      config.icon
    ] ?? LucideIcons.Package;

  return {
    label: config.label,
    Icon,
  };
}

function GroupArtifactRow({
  group,
  artifactId,
  addedAt,
}: {
  group: Group;
  artifactId: string;
  addedAt: string;
}) {
  const { data: artifact } = useArtifact(artifactId);
  const artifactType = inferArtifactType(artifact?.type, artifactId);
  const { label, Icon } = getArtifactTypePresentation(artifactType);
  const href = `/collection?${new URLSearchParams({
    collection: group.collection_id,
    group: group.id,
    artifact: artifactId,
  }).toString()}`;

  return (
    <Link
      href={href}
      className="flex items-center justify-between rounded-md border px-3 py-2.5 transition-colors hover:bg-muted/40"
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium">{artifact?.name ?? artifactId}</p>
        <div className="mt-1 flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="gap-1">
            <Icon className="h-3 w-3" />
            {label}
          </Badge>
          <span className="text-xs text-muted-foreground">
            Added {new Date(addedAt).toLocaleDateString()}
          </span>
        </div>
      </div>
      <ArrowUpRight className="h-4 w-4 text-muted-foreground" aria-hidden />
    </Link>
  );
}

function ArtifactHistoryRow({ artifactId }: { artifactId: string }) {
  const { data: artifact } = useArtifact(artifactId);
  const artifactType = inferArtifactType(artifact?.type, artifactId);
  const { label } = getArtifactTypePresentation(artifactType);

  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-medium">{artifact?.name ?? artifactId}</span>
      <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
        {label}
      </Badge>
    </span>
  );
}

export function GroupDetailsModal({ open, onOpenChange, group }: GroupDetailsModalProps) {
  const { toast } = useToast();
  const updateGroup = useUpdateGroup();

  const groupId = group?.id;
  const { data: detailedGroup } = useGroup(groupId ?? undefined);
  const { data: artifacts = [], isLoading: isLoadingArtifacts } = useGroupArtifacts(
    groupId ?? undefined
  );

  const [localTags, setLocalTags] = useState<string[]>([]);
  const [localColor, setLocalColor] = useState<GroupColor>('slate');
  const [localIcon, setLocalIcon] = useState<GroupIcon>('layers');
  const [isMetadataSaving, setIsMetadataSaving] = useState(false);

  useEffect(() => {
    const source = detailedGroup ?? group;
    if (!source) {
      return;
    }

    setLocalTags(source.tags ?? []);
    setLocalColor((source.color as GroupColor) ?? 'slate');
    setLocalIcon((source.icon as GroupIcon) ?? 'layers');
  }, [group, detailedGroup]);

  const sortedHistory = useMemo(() => {
    return [...artifacts].sort(
      (a, b) => new Date(b.added_at).getTime() - new Date(a.added_at).getTime()
    );
  }, [artifacts]);

  const persistMetadata = async (
    nextData: { tags?: string[]; color?: GroupColor; icon?: GroupIcon },
    options: {
      onRollback?: () => void;
      failureTitle: string;
      failureDescription: string;
    }
  ) => {
    if (!group) {
      return;
    }

    setIsMetadataSaving(true);
    try {
      await updateGroup.mutateAsync({
        id: group.id,
        data: nextData,
      });
    } catch (error) {
      options.onRollback?.();
      toast({
        title: options.failureTitle,
        description:
          error instanceof Error && error.message ? error.message : options.failureDescription,
        variant: 'destructive',
      });
    } finally {
      setIsMetadataSaving(false);
    }
  };

  const handleTagsChange = async (nextTags: string[]) => {
    const { tags, invalidTags, truncated } = sanitizeGroupTags(nextTags);

    if (invalidTags.length > 0) {
      toast({
        title: 'Invalid tags removed',
        description: 'Use 1-32 characters from [a-z0-9_-].',
        variant: 'destructive',
      });
    }

    if (truncated) {
      toast({
        title: 'Tag limit reached',
        description: 'A group can have up to 20 tags.',
      });
    }

    const isSame =
      tags.length === localTags.length && tags.every((tag, index) => tag === localTags[index]);
    if (isSame) {
      return;
    }

    const previousTags = localTags;
    setLocalTags(tags);
    await persistMetadata(
      { tags },
      {
        onRollback: () => setLocalTags(previousTags),
        failureTitle: 'Tag update failed',
        failureDescription: 'Unable to save group tags.',
      }
    );
  };

  const handleColorChange = async (nextColor: GroupColor) => {
    if (nextColor === localColor) {
      return;
    }

    const previousColor = localColor;
    setLocalColor(nextColor);
    await persistMetadata(
      { color: nextColor },
      {
        onRollback: () => setLocalColor(previousColor),
        failureTitle: 'Color update failed',
        failureDescription: 'Unable to save group color.',
      }
    );
  };

  const handleIconChange = async (nextIcon: GroupIcon) => {
    if (nextIcon === localIcon) {
      return;
    }

    const previousIcon = localIcon;
    setLocalIcon(nextIcon);
    await persistMetadata(
      { icon: nextIcon },
      {
        onRollback: () => setLocalIcon(previousIcon),
        failureTitle: 'Icon update failed',
        failureDescription: 'Unable to save group icon.',
      }
    );
  };

  if (!group) {
    return null;
  }

  const displayGroup = detailedGroup ?? group;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex h-[88vh] max-w-5xl flex-col gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b px-6 py-4">
          <DialogTitle>{displayGroup.name}</DialogTitle>
          <DialogDescription>Group details, artifacts, and change history.</DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="overview" className="flex min-h-0 flex-1 flex-col">
          <TabsList className="mx-6 mt-4 w-fit justify-start">
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

          <TabsContent value="overview" className="mt-4 min-h-0 flex-1 overflow-y-auto px-6 pb-6">
            <div className="space-y-6">
              <div>
                <p className="text-sm font-medium">Description</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {displayGroup.description || 'No description provided.'}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
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

              <div className="rounded-lg border p-4">
                <GroupMetadataEditor
                  tags={localTags}
                  onTagsChange={(tags) => void handleTagsChange(tags)}
                  color={localColor}
                  onColorChange={(color) => void handleColorChange(color)}
                  icon={localIcon}
                  onIconChange={(icon) => void handleIconChange(icon)}
                  availableTags={localTags}
                  disabled={isMetadataSaving}
                />
              </div>
            </div>
          </TabsContent>

          <TabsContent value="artifacts" className="mt-4 min-h-0 flex-1 overflow-y-auto px-6 pb-6">
            <div className="space-y-3">
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
                    <GroupArtifactRow
                      key={artifact.artifact_id}
                      group={group}
                      artifactId={artifact.artifact_id}
                      addedAt={artifact.added_at}
                    />
                  ))}
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="history" className="mt-4 min-h-0 flex-1 overflow-y-auto px-6 pb-6">
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Showing membership events from currently persisted group data. Removal events are
                shown when the API persists group-history removals.
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
