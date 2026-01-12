'use client';

import { useState, useEffect } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Loader2, X, CheckCircle2 } from 'lucide-react';
import { EntityType, EntityFormField, ENTITY_TYPES, Entity } from '@/types/entity';
import {
  useEntityLifecycle,
  useGitHubMetadata,
  useTags,
  useArtifactTags,
  useAddTagToArtifact,
  useRemoveTagFromArtifact,
  useCreateTag,
} from '@/hooks';
import { useDebouncedCallback } from 'use-debounce';
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
import { TagInput, type Tag } from '@/components/ui/tag-input';

/**
 * Props for EntityForm component
 *
 * Controls form mode (create vs edit), entity data, and submission callbacks.
 */
interface EntityFormProps {
  /** Mode: 'create' for new entities, 'edit' for existing entities */
  mode: 'create' | 'edit';
  /** Entity type configuration - required for create mode, determines available form fields */
  entityType?: EntityType;
  /** Existing entity data - required for edit mode to populate form values */
  entity?: Entity;
  /** Callback function called after successful form submission */
  onSuccess?: () => void;
  /** Callback function called when user clicks cancel */
  onCancel?: () => void;
}

interface FormData {
  name: string;
  source: string;
  sourceType: 'github' | 'local';
  description?: string;
  tags?: string[];
  [key: string]: any;
}

/**
 * EntityForm - Create or edit entity form
 *
 * Renders a dynamic form for creating new entities or editing existing ones.
 * In create mode, shows all fields from the entity type schema plus source type selection (GitHub/Local).
 * In edit mode, only shows editable fields (tags and description).
 * Supports dynamic field rendering based on entity type (text, textarea, select, tags, boolean).
 *
 * @example
 * ```tsx
 * // Create mode
 * <EntityForm
 *   mode="create"
 *   entityType="skill"
 *   onSuccess={() => closeDialog()}
 *   onCancel={() => closeDialog()}
 * />
 *
 * // Edit mode
 * <EntityForm
 *   mode="edit"
 *   entity={existingSkill}
 *   onSuccess={() => refetchData()}
 *   onCancel={() => closeDialog()}
 * />
 * ```
 *
 * @param props - EntityFormProps configuration
 * @returns Form component for creating or editing entities
 */
export function EntityForm({ mode, entityType, entity, onSuccess, onCancel }: EntityFormProps) {
  const { createEntity, updateEntity } = useEntityLifecycle();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceType, setSourceType] = useState<'github' | 'local'>('github');
  const [selectedTagIds, setSelectedTagIds] = useState<string[]>([]);

  // GitHub metadata auto-population
  const { mutate: fetchMetadata, data: metadata, isPending: isMetadataLoading } = useGitHubMetadata();

  // Fetch available tags for suggestions
  const { data: tagsData } = useTags(100);
  const { data: currentTags } = useArtifactTags(entity?.id);

  // Tag mutations
  const addTag = useAddTagToArtifact();
  const removeTag = useRemoveTagFromArtifact();
  const createTag = useCreateTag();

  // Transform tags for TagInput
  const tagSuggestions: Tag[] = tagsData?.items?.map(t => ({
    id: t.id,
    name: t.name,
    slug: t.slug,
    color: t.color,
  })) || [];

  // Determine the entity type config
  const typeConfig = entityType
    ? ENTITY_TYPES[entityType]
    : entity
      ? ENTITY_TYPES[entity.type]
      : null;

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    getValues,
    control,
  } = useForm<FormData>({
    defaultValues: {
      name: entity?.name || '',
      source: entity?.source || '',
      sourceType: 'github',
      description: entity?.description || '',
      tags: entity?.tags || [],
    },
  });

  // Initialize selected tags when entity or current tags change
  useEffect(() => {
    if (currentTags && currentTags.length > 0) {
      setSelectedTagIds(currentTags.map(tag => tag.id));
    } else if (entity?.tags) {
      // If we have tag names but not IDs, try to match them
      const matchedTagIds = entity.tags
        .map(tagName => {
          const tag = tagSuggestions.find(t => t.name === tagName || t.slug === tagName);
          return tag?.id;
        })
        .filter((id): id is string => id !== undefined);
      setSelectedTagIds(matchedTagIds);
    }
  }, [entity, currentTags, tagSuggestions]);

  // Auto-populate fields when GitHub metadata arrives
  useEffect(() => {
    if (metadata && mode === 'create') {
      // Only auto-populate if fields are empty
      const currentName = getValues('name');
      const currentDesc = getValues('description');

      if (!currentName && metadata.title) {
        setValue('name', metadata.title);
      }
      if (!currentDesc && metadata.description) {
        setValue('description', metadata.description);
      }
      // Auto-populate tags from GitHub topics
      if (metadata.topics && metadata.topics.length > 0 && selectedTagIds.length === 0) {
        // Try to match GitHub topics to existing tags
        const matchedTagIds = metadata.topics
          .map(topic => {
            const tag = tagSuggestions.find(t => t.slug === topic.toLowerCase());
            return tag?.id;
          })
          .filter((id): id is string => id !== undefined);

        if (matchedTagIds.length > 0) {
          setSelectedTagIds(matchedTagIds);
        }
      }
    }
  }, [metadata, mode, setValue, getValues, selectedTagIds.length, tagSuggestions]);

  // Debounced GitHub metadata fetch
  const handleSourceChange = useDebouncedCallback((source: string) => {
    if (sourceType === 'github' && source.includes('/')) {
      fetchMetadata(source);
    }
  }, 500);

  // Get editable fields based on mode
  const getFields = (): EntityFormField[] => {
    if (!typeConfig) return [];

    if (mode === 'edit') {
      // In edit mode, only show editable fields (description, but NOT tags - we handle that separately)
      return typeConfig.formSchema.fields.filter(
        (field) => field.name === 'description'
      );
    }

    // In create mode, filter out tags field (we handle it separately with TagInput)
    return typeConfig.formSchema.fields.filter(field => field.name !== 'tags');
  };

  const fields = getFields();

  // Handle tag changes
  const handleTagsChange = async (newTagIds: string[]) => {
    if (!entity?.id) {
      // In create mode, just update state
      setSelectedTagIds(newTagIds);
      return;
    }

    // In edit mode, apply changes to backend
    try {
      // Find added tags
      const added = newTagIds.filter(id => !selectedTagIds.includes(id));
      // Find removed tags
      const removed = selectedTagIds.filter(id => !newTagIds.includes(id));

      // Apply changes
      for (const tagId of added) {
        await addTag.mutateAsync({ artifactId: entity.id, tagId });
      }
      for (const tagId of removed) {
        await removeTag.mutateAsync({ artifactId: entity.id, tagId });
      }

      setSelectedTagIds(newTagIds);
    } catch (err) {
      console.error('Failed to update tags:', err);
      setError(err instanceof Error ? err.message : 'Failed to update tags');
    }
  };

  // Form submission
  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);
    setError(null);

    try {
      if (mode === 'create') {
        if (!entityType) {
          throw new Error('Entity type is required for create mode');
        }

        // Convert tag IDs to tag names for creation
        const tagNames = selectedTagIds
          .map(id => tagSuggestions.find(t => t.id === id)?.name)
          .filter((name): name is string => name !== undefined);

        await createEntity({
          name: data.name,
          type: entityType,
          source: data.source,
          sourceType: sourceType,
          tags: tagNames,
          description: data.description,
        });
      } else {
        if (!entity) {
          throw new Error('Entity is required for edit mode');
        }

        await updateEntity(entity.id, {
          description: data.description,
        });
      }

      onSuccess?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Render field based on type
  const renderField = (field: EntityFormField) => {
    const fieldId = `field-${field.name}`;

    // Skip source field if we're rendering it separately
    if (field.name === 'source' && mode === 'create') {
      return null;
    }

    switch (field.type) {
      case 'text':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="ml-1 text-destructive">*</span>}
            </Label>
            <Input
              id={fieldId}
              {...register(field.name, {
                required: field.required ? `${field.label} is required` : false,
                pattern:
                  field.name === 'name'
                    ? {
                        value: /^[a-zA-Z0-9-_]+$/,
                        message:
                          'Name must contain only alphanumeric characters, hyphens, and underscores',
                      }
                    : undefined,
              })}
              placeholder={field.placeholder}
              disabled={mode === 'edit'}
            />
            {errors[field.name] && (
              <p className="text-sm text-destructive">{errors[field.name]?.message as string}</p>
            )}
          </div>
        );

      case 'textarea':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="ml-1 text-destructive">*</span>}
            </Label>
            <Textarea
              id={fieldId}
              {...register(field.name, {
                required: field.required ? `${field.label} is required` : false,
              })}
              placeholder={field.placeholder}
              rows={3}
            />
            {errors[field.name] && (
              <p className="text-sm text-destructive">{errors[field.name]?.message as string}</p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="ml-1 text-destructive">*</span>}
            </Label>
            <Controller
              name={field.name}
              control={control}
              rules={{
                required: field.required ? `${field.label} is required` : false,
              }}
              render={({ field: { onChange, value } }) => (
                <Select value={value} onValueChange={onChange}>
                  <SelectTrigger id={fieldId}>
                    <SelectValue placeholder={`Select ${field.label.toLowerCase()}...`} />
                  </SelectTrigger>
                  <SelectContent>
                    {field.options?.map((option) => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            />
            {errors[field.name] && (
              <p className="text-sm text-destructive">{errors[field.name]?.message as string}</p>
            )}
          </div>
        );

      case 'boolean':
        return (
          <div key={field.name} className="flex items-center space-x-2">
            <Checkbox id={fieldId} {...register(field.name)} />
            <Label htmlFor={fieldId} className="text-sm font-normal">
              {field.label}
            </Label>
          </div>
        );

      default:
        return null;
    }
  };

  if (!typeConfig) {
    return <div className="py-8 text-center text-muted-foreground">Invalid entity type</div>;
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Error message */}
      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Source type selection (create mode only) */}
      {mode === 'create' && (
        <>
          <div className="space-y-2">
            <Label>Source Type</Label>
            <div className="flex gap-4">
              <label className="flex cursor-pointer items-center space-x-2">
                <input
                  type="radio"
                  name="sourceType"
                  value="github"
                  checked={sourceType === 'github'}
                  onChange={() => setSourceType('github')}
                  className="h-4 w-4 text-primary focus:ring-primary"
                />
                <span className="text-sm">GitHub</span>
              </label>
              <label className="flex cursor-pointer items-center space-x-2">
                <input
                  type="radio"
                  name="sourceType"
                  value="local"
                  checked={sourceType === 'local'}
                  onChange={() => setSourceType('local')}
                  className="h-4 w-4 text-primary focus:ring-primary"
                />
                <span className="text-sm">Local</span>
              </label>
            </div>
          </div>

          {/* Source input */}
          <div className="space-y-2">
            <Label htmlFor="source">
              Source
              <span className="ml-1 text-destructive">*</span>
            </Label>
            <div className="relative">
              <Input
                id="source"
                {...register('source', {
                  required: 'Source is required',
                  onChange: (e) => handleSourceChange(e.target.value),
                })}
                placeholder={
                  sourceType === 'github' ? 'owner/repo/path[@version]' : '/absolute/path/to/artifact'
                }
              />
              {isMetadataLoading && (
                <Loader2 className="absolute right-3 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
              )}
              {metadata && !isMetadataLoading && (
                <CheckCircle2 className="absolute right-3 top-2.5 h-4 w-4 text-green-600" />
              )}
            </div>
            <p className="text-xs text-muted-foreground">
              {sourceType === 'github'
                ? 'Example: anthropics/skills/canvas-design@v2.1.0'
                : 'Provide the absolute path to the artifact directory'}
            </p>
            {metadata && !isMetadataLoading && (
              <p className="text-sm text-green-600 flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3" />
                Metadata fetched - fields auto-populated
              </p>
            )}
            {errors.source && (
              <p className="text-sm text-destructive">{errors.source.message as string}</p>
            )}
          </div>
        </>
      )}

      {/* Dynamic fields */}
      {fields.map((field) => renderField(field))}

      {/* Tags section - always shown */}
      <div className="space-y-2">
        <Label htmlFor="tags">Tags</Label>
        <TagInput
          value={selectedTagIds}
          onChange={handleTagsChange}
          suggestions={tagSuggestions}
          placeholder="Add tags..."
          allowCreate={true}
        />
        <p className="text-xs text-muted-foreground">
          Press Enter or comma to add tags. Create new tags by typing.
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex justify-end gap-3 border-t pt-4">
        {onCancel && (
          <Button type="button" variant="outline" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              {mode === 'create' ? 'Adding...' : 'Saving...'}
            </>
          ) : mode === 'create' ? (
            `Add ${typeConfig.label}`
          ) : (
            `Save Changes`
          )}
        </Button>
      </div>
    </form>
  );
}
