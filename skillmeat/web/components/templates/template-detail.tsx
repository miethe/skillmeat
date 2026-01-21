'use client';

import { FileText, File, FileCode, BookOpen, Calendar, CheckCircle2, Upload } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface TemplateEntity {
  artifact_id: string;
  name: string;
  type: string;
  deploy_order: number;
  required: boolean;
  path_pattern: string | null;
}

export interface TemplateDetailProps {
  template: {
    id: string;
    name: string;
    description: string | null;
    entities: TemplateEntity[];
    entity_count: number;
    created_at: string;
    updated_at: string;
  };
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDeploy?: () => void;
}

const entityTypeIcons: Record<string, React.ReactNode> = {
  project_config: <FileText className="h-4 w-4" />,
  spec_file: <File className="h-4 w-4" />,
  rule_file: <FileCode className="h-4 w-4" />,
  context_file: <BookOpen className="h-4 w-4" />,
  progress_template: <FileText className="h-4 w-4" />,
};

const entityTypeLabels: Record<string, string> = {
  project_config: 'Config',
  spec_file: 'Spec',
  rule_file: 'Rule',
  context_file: 'Context',
  progress_template: 'Progress',
};

const entityTypeColors: Record<string, string> = {
  project_config: 'bg-purple-500/10 text-purple-700 dark:text-purple-300',
  spec_file: 'bg-blue-500/10 text-blue-700 dark:text-blue-300',
  rule_file: 'bg-green-500/10 text-green-700 dark:text-green-300',
  context_file: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-300',
  progress_template: 'bg-orange-500/10 text-orange-700 dark:text-orange-300',
};

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Build a visual tree structure from entity paths
 */
function buildPathTree(entities: TemplateEntity[]): Map<string, Set<string>> {
  const tree = new Map<string, Set<string>>();

  entities.forEach((entity) => {
    if (!entity.path_pattern) return;

    const parts = entity.path_pattern.split('/');
    let currentPath = '';

    parts.forEach((part) => {
      const parentPath = currentPath;
      currentPath = currentPath ? `${currentPath}/${part}` : part;

      if (!tree.has(parentPath)) {
        tree.set(parentPath, new Set());
      }
      tree.get(parentPath)!.add(currentPath);
    });
  });

  return tree;
}

function PathTreeNode({
  path,
  tree,
  entities,
  level = 0,
}: {
  path: string;
  tree: Map<string, Set<string>>;
  entities: TemplateEntity[];
  level?: number;
}) {
  const children = Array.from(tree.get(path) || []).sort();
  const pathName = path.split('/').pop() || path;
  const isFile = !tree.has(path) || tree.get(path)!.size === 0;

  // Find entity with this exact path
  const entity = entities.find((e) => e.path_pattern === path);

  return (
    <div className="text-sm">
      <div className="flex items-center gap-2 py-0.5">
        <span className="text-muted-foreground" style={{ paddingLeft: `${level * 16}px` }}>
          {level > 0 && '├─ '}
        </span>
        {isFile ? (
          <FileText className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <span className="font-mono text-muted-foreground">📁</span>
        )}
        <span className={isFile ? 'font-mono' : 'font-semibold'}>{pathName}</span>
        {entity && (
          <>
            <Badge variant="outline" className={`text-xs ${entityTypeColors[entity.type] || ''}`}>
              {entityTypeLabels[entity.type] || entity.type}
            </Badge>
            {entity.required ? (
              <Badge variant="default" className="gap-1 text-xs">
                <CheckCircle2 className="h-3 w-3" />
                Required
              </Badge>
            ) : (
              <Badge variant="secondary" className="text-xs">
                Optional
              </Badge>
            )}
          </>
        )}
      </div>
      {children.map((childPath) => (
        <PathTreeNode
          key={childPath}
          path={childPath}
          tree={tree}
          entities={entities}
          level={level + 1}
        />
      ))}
    </div>
  );
}

export function TemplateDetail({ template, open, onOpenChange, onDeploy }: TemplateDetailProps) {
  // Sort entities by deploy_order
  const sortedEntities = [...template.entities].sort((a, b) => a.deploy_order - b.deploy_order);

  // Build path tree for visualization
  const pathTree = buildPathTree(template.entities);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] max-w-4xl flex-col overflow-hidden p-0">
        {/* Header Section - Fixed */}
        <div className="border-b px-6 pb-4 pt-6">
          <DialogHeader>
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0 rounded-lg bg-primary/10 p-3">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="min-w-0 flex-1 space-y-2">
                <DialogTitle className="text-2xl">{template.name}</DialogTitle>
                <DialogDescription>
                  {template.description || 'No description provided'}
                </DialogDescription>
                <div className="flex items-center gap-4 pt-2 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <FileText className="h-3.5 w-3.5" />
                    <span>{template.entity_count} entities</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>Updated {formatDate(template.updated_at)}</span>
                  </div>
                </div>
              </div>
            </div>
          </DialogHeader>
        </div>

        {/* Scrollable Content */}
        <ScrollArea className="flex-1 px-6">
          <div className="space-y-6 py-4">
            {/* Entities Section */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground">
                Entities ({template.entity_count})
              </h3>

              <div className="space-y-2">
                {sortedEntities.map((entity) => (
                  <div
                    key={entity.artifact_id}
                    className="flex items-start gap-3 rounded-lg border bg-muted/30 p-3"
                  >
                    <div className="flex-shrink-0 rounded bg-background p-2">
                      {entityTypeIcons[entity.type] || <FileText className="h-4 w-4" />}
                    </div>
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <h4 className="font-medium">{entity.name}</h4>
                        <Badge
                          variant="outline"
                          className={`text-xs ${entityTypeColors[entity.type] || ''}`}
                        >
                          {entityTypeLabels[entity.type] || entity.type}
                        </Badge>
                        {entity.required ? (
                          <Badge variant="default" className="gap-1 text-xs">
                            <CheckCircle2 className="h-3 w-3" />
                            Required
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">
                            Optional
                          </Badge>
                        )}
                      </div>
                      {entity.path_pattern && (
                        <p className="truncate font-mono text-xs text-muted-foreground">
                          {entity.path_pattern}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        Deploy order: {entity.deploy_order}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <Separator />

            {/* Structure Tree Preview */}
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-foreground">Project Structure</h3>

              <div className="rounded-lg border bg-muted/50 p-4">
                <div className="font-mono text-sm">
                  {Array.from(pathTree.get('') || [])
                    .sort()
                    .map((rootPath) => (
                      <PathTreeNode
                        key={rootPath}
                        path={rootPath}
                        tree={pathTree}
                        entities={template.entities}
                      />
                    ))}
                </div>
              </div>

              <div className="rounded-lg border border-muted bg-muted/30 p-4">
                <p className="text-xs text-muted-foreground">
                  <strong>Note:</strong> This structure will be created in your project's{' '}
                  <code className="rounded bg-background px-1 py-0.5">.claude/</code> directory when
                  you deploy this template.
                </p>
              </div>
            </div>

            {/* Metadata */}
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Metadata</h3>
              <div className="grid grid-cols-2 gap-4">
                <MetadataItem
                  icon={<Calendar className="h-4 w-4" />}
                  label="Created"
                  value={formatDate(template.created_at)}
                />
                <MetadataItem
                  icon={<Calendar className="h-4 w-4" />}
                  label="Updated"
                  value={formatDate(template.updated_at)}
                />
                <MetadataItem
                  icon={<FileText className="h-4 w-4" />}
                  label="Template ID"
                  value={template.id}
                />
                <MetadataItem
                  icon={<FileText className="h-4 w-4" />}
                  label="Entity Count"
                  value={String(template.entity_count)}
                />
              </div>
            </div>
          </div>
        </ScrollArea>

        {/* Footer Actions - Fixed */}
        <DialogFooter className="border-t bg-muted/30 px-6 py-4">
          <div className="flex w-full items-center justify-between">
            <Button variant="ghost" onClick={() => onOpenChange(false)}>
              Close
            </Button>
            {onDeploy && (
              <Button variant="default" onClick={onDeploy}>
                <Upload className="mr-2 h-4 w-4" />
                Deploy Template
              </Button>
            )}
          </div>
        </DialogFooter>
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
