'use client';

import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Loader2 } from 'lucide-react';
import {
  ContextEntity,
  CreateContextEntityRequest,
  UpdateContextEntityRequest,
  ContextEntityType,
} from '@/types/context-entity';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { MarkdownEditor } from '@/components/editor/markdown-editor';

/**
 * Props for ContextEntityEditor component
 *
 * Controls form mode (create vs edit) and provides callbacks for save/cancel actions.
 */
export interface ContextEntityEditorProps {
  /** Entity to edit (undefined for create mode) */
  entity?: ContextEntity;
  /** Initial markdown content (for create mode) */
  initialContent?: string;
  /** Callback when form is saved */
  onSave: (data: CreateContextEntityRequest | UpdateContextEntityRequest) => void;
  /** Callback when form is cancelled */
  onCancel: () => void;
  /** Whether save operation is in progress */
  isLoading?: boolean;
}

interface FormData {
  name: string;
  entity_type: ContextEntityType;
  path_pattern: string;
  description?: string;
  category?: string;
  auto_load: boolean;
  version?: string;
  content: string;
}

/**
 * Entity type options for select dropdown
 */
const ENTITY_TYPE_OPTIONS: Array<{ value: ContextEntityType; label: string; description: string }> =
  [
    {
      value: 'project_config',
      label: 'Project Config',
      description: 'Configuration files (e.g., .claude/config.toml)',
    },
    {
      value: 'spec_file',
      label: 'Spec File',
      description: 'Specification documents (e.g., .claude/specs/*.md)',
    },
    {
      value: 'rule_file',
      label: 'Rule File',
      description: 'Path-scoped rules (e.g., .claude/rules/web/*.md)',
    },
    {
      value: 'context_file',
      label: 'Context File',
      description: 'Knowledge documents (e.g., .claude/context/*.md)',
    },
    {
      value: 'progress_template',
      label: 'Progress Template',
      description: 'Progress tracking templates',
    },
  ];

/**
 * ContextEntityEditor - Create or edit context entity form
 *
 * Provides a two-column layout (desktop) or stacked layout (mobile) for editing
 * context entity metadata and markdown content. Includes real-time validation
 * and an inline markdown editor.
 *
 * Features:
 * - Metadata fields (name, type, path pattern, description, category, auto-load, version)
 * - CodeMirror-based markdown editor
 * - Real-time validation feedback
 * - Save/cancel actions
 * - Loading state support
 *
 * @example
 * ```tsx
 * // Create mode
 * <ContextEntityEditor
 *   initialContent="# New Context Entity\n..."
 *   onSave={(data) => createContextEntity(data)}
 *   onCancel={() => closeDialog()}
 *   isLoading={isCreating}
 * />
 *
 * // Edit mode
 * <ContextEntityEditor
 *   entity={existingEntity}
 *   onSave={(data) => updateContextEntity(entity.id, data)}
 *   onCancel={() => closeDialog()}
 *   isLoading={isUpdating}
 * />
 * ```
 */
export function ContextEntityEditor({
  entity,
  initialContent = '',
  onSave,
  onCancel,
  isLoading = false,
}: ContextEntityEditorProps) {
  const [markdownContent, setMarkdownContent] = useState<string>(
    entity?.content_hash || initialContent
  );
  const [error, setError] = useState<string | null>(null);

  // Determine if we're in edit mode
  const isEditMode = !!entity;

  // Form setup with react-hook-form
  const {
    register,
    handleSubmit,
    formState: { errors },
    control,
    watch,
  } = useForm<FormData>({
    defaultValues: {
      name: entity?.name || '',
      entity_type: entity?.entity_type || 'context_file',
      path_pattern: entity?.path_pattern || '.claude/',
      description: entity?.description || '',
      category: entity?.category || '',
      auto_load: entity?.auto_load || false,
      version: entity?.version || '',
      content: entity?.content_hash || initialContent,
    },
  });

  // Watch auto_load value for checkbox
  const autoLoadValue = watch('auto_load');

  // Update markdown content when entity changes
  useEffect(() => {
    if (entity?.content_hash) {
      setMarkdownContent(entity.content_hash);
    }
  }, [entity?.content_hash]);

  // Form submission
  const onSubmit = async (data: FormData) => {
    setError(null);

    try {
      // Validate path pattern
      if (!data.path_pattern.startsWith('.claude/')) {
        setError("Path pattern must start with '.claude/'");
        return;
      }

      if (data.path_pattern.includes('..')) {
        setError("Path pattern cannot contain '..' for security reasons");
        return;
      }

      // Validate name length
      if (data.name.length < 1 || data.name.length > 255) {
        setError('Name must be between 1 and 255 characters');
        return;
      }

      // Validate content
      if (!markdownContent.trim()) {
        setError('Content is required');
        return;
      }

      // Build request data
      const requestData: CreateContextEntityRequest | UpdateContextEntityRequest = {
        name: data.name,
        entity_type: data.entity_type,
        content: markdownContent,
        path_pattern: data.path_pattern,
        description: data.description || undefined,
        category: data.category || undefined,
        auto_load: data.auto_load,
        version: data.version || undefined,
      };

      onSave(requestData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex h-full flex-col">
      {/* Error message */}
      {error && (
        <div
          role="alert"
          aria-live="assertive"
          className="mb-4 rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive"
        >
          {error}
        </div>
      )}

      {/* Two-column layout (desktop) / stacked (mobile) */}
      <div className="flex flex-1 flex-col gap-6 overflow-hidden lg:flex-row">
        {/* Left column: Metadata fields */}
        <div className="space-y-4 overflow-auto lg:w-1/3 lg:pr-6">
          {/* Name field */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Name
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <Input
              id="name"
              {...register('name', {
                required: 'Name is required',
                minLength: { value: 1, message: 'Name must be at least 1 character' },
                maxLength: { value: 255, message: 'Name must be at most 255 characters' },
              })}
              placeholder="e.g., web-hooks-rules"
              disabled={isLoading}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>

          {/* Entity type field */}
          <div className="space-y-2">
            <Label htmlFor="entity_type">
              Entity Type
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <Controller
              name="entity_type"
              control={control}
              rules={{ required: 'Entity type is required' }}
              render={({ field: { onChange, value } }) => (
                <Select value={value} onValueChange={onChange} disabled={isLoading}>
                  <SelectTrigger id="entity_type">
                    <SelectValue placeholder="Select entity type..." />
                  </SelectTrigger>
                  <SelectContent>
                    {ENTITY_TYPE_OPTIONS.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        <div>
                          <div className="font-medium">{option.label}</div>
                          <div className="text-xs text-muted-foreground">{option.description}</div>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors.entity_type && (
              <p className="text-sm text-destructive">{errors.entity_type.message}</p>
            )}
          </div>

          {/* Path pattern field */}
          <div className="space-y-2">
            <Label htmlFor="path_pattern">
              Path Pattern
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <Input
              id="path_pattern"
              {...register('path_pattern', {
                required: 'Path pattern is required',
                pattern: {
                  value: /^\.claude\//,
                  message: "Path pattern must start with '.claude/'",
                },
                validate: (value) => {
                  if (value.includes('..')) {
                    return "Path pattern cannot contain '..' for security reasons";
                  }
                  return true;
                },
              })}
              placeholder="e.g., .claude/rules/web/hooks.md"
              disabled={isLoading}
              aria-describedby="path_pattern-help"
            />
            <p id="path_pattern-help" className="text-xs text-muted-foreground">
              Must start with <code className="rounded bg-muted px-1 py-0.5">.claude/</code>
            </p>
            {errors.path_pattern && (
              <p className="text-sm text-destructive" role="alert">{errors.path_pattern.message}</p>
            )}
          </div>

          {/* Description field */}
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              {...register('description')}
              placeholder="Detailed description of this context entity..."
              rows={3}
              disabled={isLoading}
            />
          </div>

          {/* Category field */}
          <div className="space-y-2">
            <Label htmlFor="category">Category</Label>
            <Input
              id="category"
              {...register('category')}
              placeholder="e.g., api, frontend, debugging"
              disabled={isLoading}
              aria-describedby="category-help"
            />
            <p id="category-help" className="text-xs text-muted-foreground">
              For progressive disclosure grouping
            </p>
          </div>

          {/* Auto-load checkbox */}
          <div className="flex items-start space-x-3 space-y-0">
            <Controller
              name="auto_load"
              control={control}
              render={({ field: { onChange, value } }) => (
                <Checkbox
                  id="auto_load"
                  checked={value}
                  onCheckedChange={onChange}
                  disabled={isLoading}
                  aria-describedby="auto_load-help"
                />
              )}
            />
            <div className="space-y-1">
              <Label htmlFor="auto_load" className="text-sm font-normal">
                Auto-load when path pattern matches edited files
              </Label>
              <p id="auto_load-help" className="text-xs text-muted-foreground">
                Enable for path-scoped rules and context files
              </p>
            </div>
          </div>

          {/* Version field */}
          <div className="space-y-2">
            <Label htmlFor="version">Version</Label>
            <Input
              id="version"
              {...register('version')}
              placeholder="e.g., 1.0.0"
              disabled={isLoading}
              aria-describedby="version-help"
            />
            <p id="version-help" className="text-xs text-muted-foreground">Semantic versioning recommended</p>
          </div>
        </div>

        {/* Right column: Markdown editor */}
        <div className="flex flex-1 flex-col space-y-2 overflow-hidden lg:w-2/3">
          <Label htmlFor="content">
            Content
            <span className="ml-1 text-destructive">*</span>
          </Label>
          <div className="flex-1 overflow-hidden">
            <MarkdownEditor
              initialContent={markdownContent}
              onChange={setMarkdownContent}
              readOnly={isLoading}
              className="h-full"
            />
          </div>
          <p id="content-help" className="text-xs text-muted-foreground">
            Markdown content for this context entity
          </p>
        </div>
      </div>

      {/* Action buttons */}
      <div className="mt-6 flex justify-end gap-3 border-t pt-4">
        <Button type="button" variant="outline" onClick={onCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {isEditMode ? 'Saving...' : 'Creating...'}
            </>
          ) : isEditMode ? (
            'Save Changes'
          ) : (
            'Create Entity'
          )}
        </Button>
      </div>
    </form>
  );
}
