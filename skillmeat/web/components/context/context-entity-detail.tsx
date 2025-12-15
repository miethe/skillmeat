'use client';

import { useState } from 'react';
import {
  FileText,
  Calendar,
  Tag,
  Eye,
  EyeOff,
  Edit,
  Upload,
  X,
  Loader2,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useContextEntityContent } from '@/hooks/use-context-entities';
import type { ContextEntity, ContextEntityType } from '@/types/context-entity';

interface ContextEntityDetailProps {
  entity: ContextEntity | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeploy?: (entity: ContextEntity) => void;
  onEdit?: (entity: ContextEntity) => void;
}

const entityTypeLabels: Record<ContextEntityType, string> = {
  project_config: 'Project Config',
  spec_file: 'Specification',
  rule_file: 'Rule File',
  context_file: 'Context File',
  progress_template: 'Progress Template',
};

const entityTypeColors: Record<ContextEntityType, string> = {
  project_config: 'bg-purple-500/10 text-purple-700 dark:text-purple-300',
  spec_file: 'bg-blue-500/10 text-blue-700 dark:text-blue-300',
  rule_file: 'bg-green-500/10 text-green-700 dark:text-green-300',
  context_file: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-300',
  progress_template: 'bg-orange-500/10 text-orange-700 dark:text-orange-300',
};

function DetailSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <div className="grid grid-cols-2 gap-4">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </div>

      <div className="space-y-3">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  );
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function ContextEntityDetail({
  entity,
  open,
  onOpenChange,
  onDeploy,
  onEdit,
}: ContextEntityDetailProps) {
  const [showRawContent, setShowRawContent] = useState(false);

  // Lazy load content when modal is open
  const {
    data: content,
    isLoading: isContentLoading,
    error: contentError,
  } = useContextEntityContent(open ? entity?.id : undefined);

  const handleClose = () => {
    onOpenChange(false);
    // Reset state when closing
    setShowRawContent(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] max-w-3xl flex-col overflow-hidden p-0">
        {!entity ? (
          <div className="p-6">
            <DetailSkeleton />
          </div>
        ) : (
          <>
            {/* Header Section - Fixed */}
            <div className="border-b px-6 pb-4 pt-6">
              <DialogHeader>
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 rounded-lg bg-primary/10 p-3">
                    <FileText className="h-6 w-6 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-2">
                    <DialogTitle className="text-2xl">{entity.name}</DialogTitle>
                    <DialogDescription>{entity.description || 'No description'}</DialogDescription>
                    <div className="flex items-center gap-2 pt-1">
                      <Badge
                        variant="outline"
                        className={entityTypeColors[entity.entity_type]}
                      >
                        {entityTypeLabels[entity.entity_type]}
                      </Badge>
                      {entity.category && (
                        <Badge variant="secondary" className="capitalize">
                          {entity.category}
                        </Badge>
                      )}
                      {entity.auto_load ? (
                        <Badge variant="default" className="gap-1">
                          <Eye className="h-3 w-3" />
                          Auto-load
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="gap-1">
                          <EyeOff className="h-3 w-3" />
                          Manual
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </DialogHeader>
            </div>

            {/* Scrollable Content */}
            <ScrollArea className="flex-1 px-6">
              <div className="space-y-6 py-4">
                {/* Metadata Grid */}
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-foreground">Metadata</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <MetadataItem
                      icon={<FileText className="h-4 w-4" />}
                      label="Path Pattern"
                      value={entity.path_pattern}
                    />
                    <MetadataItem
                      icon={<Tag className="h-4 w-4" />}
                      label="Category"
                      value={entity.category || 'Uncategorized'}
                    />
                    <MetadataItem
                      icon={<Calendar className="h-4 w-4" />}
                      label="Created"
                      value={formatDate(entity.created_at)}
                    />
                    <MetadataItem
                      icon={<Calendar className="h-4 w-4" />}
                      label="Updated"
                      value={formatDate(entity.updated_at)}
                    />
                  </div>
                  {entity.version && (
                    <div className="grid grid-cols-2 gap-4">
                      <MetadataItem
                        icon={<Tag className="h-4 w-4" />}
                        label="Version"
                        value={entity.version}
                      />
                    </div>
                  )}
                </div>

                {/* Content Preview */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-sm font-semibold text-foreground">Content Preview</h3>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowRawContent(!showRawContent)}
                    >
                      {showRawContent ? 'Show Formatted' : 'Show Raw'}
                    </Button>
                  </div>

                  <div className="rounded-lg border bg-muted/50">
                    {isContentLoading ? (
                      <div className="flex items-center justify-center p-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                        <span className="ml-2 text-sm text-muted-foreground">
                          Loading content...
                        </span>
                      </div>
                    ) : contentError ? (
                      <div className="p-8 text-center">
                        <p className="text-sm text-destructive">
                          Failed to load content: {(contentError as Error).message}
                        </p>
                      </div>
                    ) : content ? (
                      <div className="max-h-96 overflow-auto">
                        {showRawContent ? (
                          <pre className="p-4 text-xs">
                            <code>{content}</code>
                          </pre>
                        ) : (
                          <div className="prose prose-sm dark:prose-invert max-w-none p-4">
                            {/* Simple markdown rendering - just show paragraphs for now */}
                            {content.split('\n\n').map((paragraph, idx) => {
                              // Handle headers
                              if (paragraph.startsWith('# ')) {
                                return (
                                  <h1 key={idx} className="text-xl font-bold">
                                    {paragraph.slice(2)}
                                  </h1>
                                );
                              }
                              if (paragraph.startsWith('## ')) {
                                return (
                                  <h2 key={idx} className="text-lg font-semibold">
                                    {paragraph.slice(3)}
                                  </h2>
                                );
                              }
                              if (paragraph.startsWith('### ')) {
                                return (
                                  <h3 key={idx} className="text-base font-semibold">
                                    {paragraph.slice(4)}
                                  </h3>
                                );
                              }
                              // Handle code blocks
                              if (paragraph.startsWith('```')) {
                                const lines = paragraph.split('\n');
                                const code = lines.slice(1, -1).join('\n');
                                return (
                                  <pre key={idx} className="rounded bg-muted p-2 text-xs">
                                    <code>{code}</code>
                                  </pre>
                                );
                              }
                              // Regular paragraph
                              return (
                                <p key={idx} className="text-sm leading-relaxed">
                                  {paragraph}
                                </p>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="p-8 text-center">
                        <p className="text-sm text-muted-foreground">No content available</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Content Hash (if available) */}
                {entity.content_hash && (
                  <div className="space-y-3">
                    <h3 className="text-sm font-semibold text-foreground">Content Hash</h3>
                    <code className="block rounded border bg-muted px-3 py-2 text-xs break-all">
                      {entity.content_hash}
                    </code>
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Actions Footer - Fixed */}
            <div className="border-t bg-muted/30 px-6 py-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex gap-2">
                  {onEdit && (
                    <Button
                      variant="outline"
                      className="justify-start"
                      onClick={() => onEdit(entity)}
                    >
                      <Edit className="mr-2 h-4 w-4" />
                      Edit
                    </Button>
                  )}
                  {onDeploy && (
                    <Button
                      variant="default"
                      className="justify-start"
                      onClick={() => onDeploy(entity)}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Deploy
                    </Button>
                  )}
                </div>
                <Button variant="ghost" onClick={handleClose}>
                  <X className="mr-2 h-4 w-4" />
                  Close
                </Button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}

function MetadataItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <p className="truncate text-sm font-medium" title={value}>
        {value}
      </p>
    </div>
  );
}
