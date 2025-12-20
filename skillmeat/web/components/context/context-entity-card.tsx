/**
 * Context Entity Card Component
 *
 * Displays a context entity with type badge, category, auto-load indicator,
 * path pattern, and action buttons. Follows the unified card style with
 * colored left border accents based on entity type.
 */

'use client';

import * as React from 'react';
import {
  FileText,
  Settings,
  BookOpen,
  FileCode,
  ListTodo,
  Eye,
  Rocket,
  Pencil,
  Trash2,
  CheckCircle2,
  Circle,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import type { ContextEntity, ContextEntityType } from '@/types/context-entity';

// ============================================================================
// Type Configuration
// ============================================================================

interface TypeConfig {
  icon: React.ElementType;
  label: string;
  borderColor: string;
  bgColor: string;
  badgeClassName: string;
}

const typeConfig: Record<ContextEntityType, TypeConfig> = {
  project_config: {
    icon: Settings,
    label: 'Config',
    borderColor: 'border-l-blue-500',
    bgColor: 'bg-blue-500/[0.02] dark:bg-blue-500/[0.03]',
    badgeClassName: 'border-blue-500 text-blue-700 bg-blue-50 dark:bg-blue-950',
  },
  spec_file: {
    icon: FileText,
    label: 'Spec',
    borderColor: 'border-l-purple-500',
    bgColor: 'bg-purple-500/[0.02] dark:bg-purple-500/[0.03]',
    badgeClassName: 'border-purple-500 text-purple-700 bg-purple-50 dark:bg-purple-950',
  },
  rule_file: {
    icon: FileCode,
    label: 'Rule',
    borderColor: 'border-l-orange-500',
    bgColor: 'bg-orange-500/[0.02] dark:bg-orange-500/[0.03]',
    badgeClassName: 'border-orange-500 text-orange-700 bg-orange-50 dark:bg-orange-950',
  },
  context_file: {
    icon: BookOpen,
    label: 'Context',
    borderColor: 'border-l-green-500',
    bgColor: 'bg-green-500/[0.02] dark:bg-green-500/[0.03]',
    badgeClassName: 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950',
  },
  progress_template: {
    icon: ListTodo,
    label: 'Progress',
    borderColor: 'border-l-yellow-500',
    bgColor: 'bg-yellow-500/[0.02] dark:bg-yellow-500/[0.03]',
    badgeClassName: 'border-yellow-500 text-yellow-700 bg-yellow-50 dark:bg-yellow-950',
  },
};

// Default config for unknown entity types
const defaultConfig: TypeConfig = {
  icon: FileText,
  label: 'Entity',
  borderColor: 'border-l-gray-500',
  bgColor: 'bg-gray-500/[0.02] dark:bg-gray-500/[0.03]',
  badgeClassName: 'border-gray-500 text-gray-700 bg-gray-50 dark:bg-gray-950',
};

// ============================================================================
// Sub-components
// ============================================================================

interface TypeBadgeProps {
  entityType: ContextEntityType;
}

function TypeBadge({ entityType }: TypeBadgeProps) {
  const config = typeConfig[entityType];
  const Icon = config.icon;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn('gap-1 text-xs', config.badgeClassName)}
          >
            <Icon className="h-3 w-3" />
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>Entity type: {config.label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

interface AutoLoadIndicatorProps {
  autoLoad: boolean;
}

function AutoLoadIndicator({ autoLoad }: AutoLoadIndicatorProps) {
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Badge
            variant="outline"
            className={cn(
              'gap-1 text-xs',
              autoLoad
                ? 'border-green-500 text-green-700 bg-green-50 dark:bg-green-950'
                : 'border-gray-300 text-gray-600 bg-gray-50 dark:bg-gray-900'
            )}
          >
            {autoLoad ? (
              <CheckCircle2 className="h-3 w-3" />
            ) : (
              <Circle className="h-3 w-3" />
            )}
            {autoLoad ? 'Auto-load' : 'Manual'}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>
            {autoLoad
              ? 'Automatically loads when path pattern matches'
              : 'Requires manual loading'}
          </p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export interface ContextEntityCardProps {
  /** The context entity to display */
  entity: ContextEntity;
  /** Callback when preview button is clicked */
  onPreview?: (entity: ContextEntity) => void;
  /** Callback when deploy button is clicked */
  onDeploy?: (entity: ContextEntity) => void;
  /** Callback when edit button is clicked */
  onEdit?: (entity: ContextEntity) => void;
  /** Callback when delete button is clicked */
  onDelete?: (entity: ContextEntity) => void;
  /** Show token count badge */
  showTokenCount?: boolean;
  /** Estimated token count for this entity */
  tokenCount?: number;
  /** Callback when auto-load toggle is changed */
  onAutoLoadToggle?: (enabled: boolean) => void;
}

/**
 * ContextEntityCard - Card for displaying a context entity
 *
 * Shows entity information including name, type, category, auto-load setting,
 * and path pattern. Provides action buttons for preview, deploy, edit, and delete.
 *
 * Visual design follows the unified card style with colored left borders based
 * on entity type (config=blue, spec=purple, rule=orange, context=green, progress=yellow).
 *
 * @example
 * ```tsx
 * <ContextEntityCard
 *   entity={contextEntity}
 *   onPreview={(entity) => showPreview(entity)}
 *   onDeploy={(entity) => deployToProject(entity)}
 *   onEdit={(entity) => openEditor(entity)}
 *   onDelete={(entity) => confirmDelete(entity)}
 * />
 * ```
 *
 * @param props - ContextEntityCardProps configuration
 * @returns Card component with entity information and actions
 */
export function ContextEntityCard({
  entity,
  onPreview,
  onDeploy,
  onEdit,
  onDelete,
  showTokenCount = false,
  tokenCount,
  onAutoLoadToggle,
}: ContextEntityCardProps) {
  // Normalize entity type to lowercase and lookup config
  const normalizedType = (entity.entity_type?.toLowerCase() || '') as ContextEntityType;
  const config = typeConfig[normalizedType] || defaultConfig;

  // Warn developers if using fallback config
  if (!typeConfig[normalizedType] && entity.entity_type) {
    console.warn(`Unknown entity type: ${entity.entity_type}, using default config`);
  }

  const Icon = config.icon;

  const handlePreview = (e: React.MouseEvent) => {
    e.stopPropagation();
    onPreview?.(entity);
  };

  const handleDeploy = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDeploy?.(entity);
  };

  const handleEdit = (e: React.MouseEvent) => {
    e.stopPropagation();
    onEdit?.(entity);
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(entity);
  };

  const handleAutoLoadToggle = (checked: boolean) => {
    onAutoLoadToggle?.(checked);
  };

  // Truncate path pattern if too long
  const truncatedPath =
    entity.path_pattern.length > 40
      ? `...${entity.path_pattern.slice(-37)}`
      : entity.path_pattern;

  return (
    <Card
      className={cn(
        'group relative border-l-4',
        config.borderColor,
        config.bgColor,
        'transition-shadow duration-200 hover:shadow-md'
      )}
      role="article"
      aria-label={`Context entity: ${entity.name}`}
    >
      <div className="p-4 space-y-3">
        {/* Header: Name + Type Badge + Auto-load */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <Icon className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <h3 className="font-semibold truncate">{entity.name}</h3>
              {entity.category && (
                <p className="text-xs text-muted-foreground">
                  Category: {entity.category}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1 flex-shrink-0">
            <TypeBadge entityType={entity.entity_type} />
            <AutoLoadIndicator autoLoad={entity.auto_load} />
          </div>
        </div>

        {/* Hover Actions */}
        {(onEdit || onDelete) && (
          <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
            {onEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                onClick={handleEdit}
                aria-label={`Edit ${entity.name}`}
              >
                <Pencil className="h-4 w-4" aria-hidden="true" />
              </Button>
            )}
            {onDelete && (
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8 text-destructive hover:text-destructive"
                onClick={handleDelete}
                aria-label={`Delete ${entity.name}`}
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </Button>
            )}
          </div>
        )}

        {/* Description */}
        {entity.description && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {entity.description}
          </p>
        )}

        {/* Path Pattern and Token Count */}
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-xs font-mono text-muted-foreground bg-muted px-2 py-1 rounded"
            title={entity.path_pattern}
            aria-label={`Path pattern: ${entity.path_pattern}`}
          >
            {truncatedPath}
          </span>
          {entity.version && (
            <Badge variant="outline" className="text-xs">
              v{entity.version}
            </Badge>
          )}
          {showTokenCount && tokenCount !== undefined && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge variant="secondary" className="text-xs gap-1">
                    ~{tokenCount} tokens
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Estimated token usage when loaded</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* Auto-load Toggle */}
        {onAutoLoadToggle && (
          <div className="flex items-center justify-between pt-2 border-t">
            <div className="flex items-center gap-2">
              <label htmlFor={`auto-load-${entity.id}`} className="text-sm font-medium cursor-pointer">
                Auto-load
              </label>
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="text-xs text-muted-foreground" aria-label="Help">ⓘ</span>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Automatically load this entity when path pattern matches</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
            <Switch
              id={`auto-load-${entity.id}`}
              checked={entity.auto_load}
              onCheckedChange={handleAutoLoadToggle}
              aria-describedby={`auto-load-help-${entity.id}`}
              aria-label={`Auto-load ${entity.name} when path pattern matches`}
            />
            <span id={`auto-load-help-${entity.id}`} className="sr-only">
              Automatically load this entity when path pattern matches edited files
            </span>
          </div>
        )}

        {/* Footer: Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t">
          {onPreview && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handlePreview}
              aria-label={`Preview ${entity.name}`}
            >
              <Eye className="h-4 w-4 mr-1" aria-hidden="true" />
              Preview
            </Button>
          )}
          {onDeploy && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleDeploy}
              aria-label={`Deploy ${entity.name} to project`}
            >
              <Rocket className="h-4 w-4 mr-1" aria-hidden="true" />
              Deploy
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
