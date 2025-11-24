'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Loader2, X } from 'lucide-react';
import { EntityType, EntityFormField, ENTITY_TYPES, Entity } from '@/types/entity';
import { useEntityLifecycle } from '@/hooks/useEntityLifecycle';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import { cn } from '@/lib/utils';

interface EntityFormProps {
  /** Mode: 'create' for new entities, 'edit' for existing */
  mode: 'create' | 'edit';
  /** Entity type - required for create mode */
  entityType?: EntityType;
  /** Existing entity data - required for edit mode */
  entity?: Entity;
  /** Called on successful submit */
  onSuccess?: () => void;
  /** Called on cancel */
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

export function EntityForm({ mode, entityType, entity, onSuccess, onCancel }: EntityFormProps) {
  const { createEntity, updateEntity } = useEntityLifecycle();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sourceType, setSourceType] = useState<'github' | 'local'>('github');
  const [tags, setTags] = useState<string[]>(entity?.tags || []);
  const [tagInput, setTagInput] = useState('');

  // Determine the entity type config
  const typeConfig = entityType ? ENTITY_TYPES[entityType] : entity ? ENTITY_TYPES[entity.type] : null;

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
    watch,
  } = useForm<FormData>({
    defaultValues: {
      name: entity?.name || '',
      source: entity?.source || '',
      sourceType: 'github',
      description: entity?.description || '',
      tags: entity?.tags || [],
    },
  });

  // Update tags in form when local tags state changes
  useEffect(() => {
    setValue('tags', tags);
  }, [tags, setValue]);

  // Get editable fields based on mode
  const getFields = (): EntityFormField[] => {
    if (!typeConfig) return [];

    if (mode === 'edit') {
      // In edit mode, only show editable fields (tags, description)
      return typeConfig.formSchema.fields.filter(
        field => field.name === 'tags' || field.name === 'description'
      );
    }

    return typeConfig.formSchema.fields;
  };

  const fields = getFields();

  // Handle tag input
  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      addTag();
    }
  };

  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !tags.includes(tag)) {
      setTags([...tags, tag]);
      setTagInput('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(t => t !== tagToRemove));
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

        await createEntity({
          name: data.name,
          type: entityType,
          source: data.source,
          sourceType: sourceType,
          tags: tags,
          description: data.description,
        });
      } else {
        if (!entity) {
          throw new Error('Entity is required for edit mode');
        }

        await updateEntity(entity.id, {
          tags: tags,
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

    // Handle tags separately
    if (field.type === 'tags') {
      return (
        <div key={field.name} className="space-y-2">
          <Label htmlFor={fieldId}>{field.label}</Label>
          <div className="space-y-2">
            {/* Existing tags */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <div
                    key={tag}
                    className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-secondary text-secondary-foreground text-sm"
                  >
                    {tag}
                    <button
                      type="button"
                      onClick={() => removeTag(tag)}
                      className="hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {/* Tag input */}
            <div className="flex gap-2">
              <Input
                id={fieldId}
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={handleTagKeyDown}
                placeholder={field.placeholder}
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                onClick={addTag}
                disabled={!tagInput.trim()}
              >
                Add
              </Button>
            </div>
          </div>
        </div>
      );
    }

    switch (field.type) {
      case 'text':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <Input
              id={fieldId}
              {...register(field.name, {
                required: field.required ? `${field.label} is required` : false,
                pattern: field.name === 'name' ? {
                  value: /^[a-zA-Z0-9-_]+$/,
                  message: 'Name must contain only alphanumeric characters, hyphens, and underscores',
                } : undefined,
              })}
              placeholder={field.placeholder}
              disabled={mode === 'edit'}
            />
            {errors[field.name] && (
              <p className="text-sm text-destructive">
                {errors[field.name]?.message as string}
              </p>
            )}
          </div>
        );

      case 'textarea':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
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
              <p className="text-sm text-destructive">
                {errors[field.name]?.message as string}
              </p>
            )}
          </div>
        );

      case 'select':
        return (
          <div key={field.name} className="space-y-2">
            <Label htmlFor={fieldId}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <Select
              id={fieldId}
              {...register(field.name, {
                required: field.required ? `${field.label} is required` : false,
              })}
            >
              <option value="">Select {field.label.toLowerCase()}...</option>
              {field.options?.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
            {errors[field.name] && (
              <p className="text-sm text-destructive">
                {errors[field.name]?.message as string}
              </p>
            )}
          </div>
        );

      case 'boolean':
        return (
          <div key={field.name} className="flex items-center space-x-2">
            <Checkbox
              id={fieldId}
              {...register(field.name)}
            />
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
    return (
      <div className="text-center py-8 text-muted-foreground">
        Invalid entity type
      </div>
    );
  }

  const title = mode === 'create'
    ? `Add New ${typeConfig.label}`
    : `Edit ${typeConfig.label}`;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Error message */}
      {error && (
        <div className="p-3 rounded-md bg-destructive/10 border border-destructive text-destructive text-sm">
          {error}
        </div>
      )}

      {/* Source type selection (create mode only) */}
      {mode === 'create' && (
        <>
          <div className="space-y-2">
            <Label>Source Type</Label>
            <div className="flex gap-4">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="sourceType"
                  value="github"
                  checked={sourceType === 'github'}
                  onChange={(e) => setSourceType('github')}
                  className="w-4 h-4 text-primary focus:ring-primary"
                />
                <span className="text-sm">GitHub</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="sourceType"
                  value="local"
                  checked={sourceType === 'local'}
                  onChange={(e) => setSourceType('local')}
                  className="w-4 h-4 text-primary focus:ring-primary"
                />
                <span className="text-sm">Local</span>
              </label>
            </div>
          </div>

          {/* Source input */}
          <div className="space-y-2">
            <Label htmlFor="source">
              Source
              <span className="text-destructive ml-1">*</span>
            </Label>
            <Input
              id="source"
              {...register('source', {
                required: 'Source is required',
              })}
              placeholder={
                sourceType === 'github'
                  ? 'owner/repo/path[@version]'
                  : '/absolute/path/to/artifact'
              }
            />
            <p className="text-xs text-muted-foreground">
              {sourceType === 'github'
                ? 'Example: anthropics/skills/canvas-design@v2.1.0'
                : 'Provide the absolute path to the artifact directory'}
            </p>
            {errors.source && (
              <p className="text-sm text-destructive">{errors.source.message as string}</p>
            )}
          </div>
        </>
      )}

      {/* Dynamic fields */}
      {fields.map(field => renderField(field))}

      {/* Action buttons */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        {onCancel && (
          <Button
            type="button"
            variant="outline"
            onClick={onCancel}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
        )}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              {mode === 'create' ? 'Adding...' : 'Saving...'}
            </>
          ) : (
            mode === 'create' ? `Add ${typeConfig.label}` : `Save Changes`
          )}
        </Button>
      </div>
    </form>
  );
}
