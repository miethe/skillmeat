'use client';

import * as React from 'react';
import { X } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { useCreateEntityTypeConfig, useUpdateEntityTypeConfig } from '@/hooks';
import { useToast } from '@/hooks';
import type { EntityTypeConfig, EntityTypeConfigCreate, EntityTypeConfigUpdate } from '@/types/context-entity';
import { IconPicker } from '@/components/shared/icon-picker';
import { ColorSelector } from '@/components/shared/color-selector';

// ---------------------------------------------------------------------------
// Platform constants
// ---------------------------------------------------------------------------

const APPLICABLE_PLATFORMS = [
  { slug: 'claude-code', label: 'Claude Code' },
  { slug: 'claude-desktop', label: 'Claude Desktop' },
  { slug: 'windsurf', label: 'Windsurf' },
  { slug: 'cursor', label: 'Cursor' },
  { slug: 'cline', label: 'Cline' },
] as const;

// ---------------------------------------------------------------------------
// Slug validation
// ---------------------------------------------------------------------------

const SLUG_RE = /^[a-z][a-z0-9_]{0,63}$/;

function validateSlug(value: string): string | undefined {
  if (!value) return 'Slug is required';
  if (!SLUG_RE.test(value))
    return 'Slug must start with a lowercase letter and contain only lowercase letters, digits, and underscores (max 64 chars)';
  return undefined;
}

// ---------------------------------------------------------------------------
// JSON validation for frontmatter_schema
// ---------------------------------------------------------------------------

function validateFrontmatterSchema(value: string): string | undefined {
  if (!value.trim()) return undefined;
  try {
    const parsed = JSON.parse(value);
    if (typeof parsed !== 'object' || Array.isArray(parsed) || parsed === null) {
      return 'Schema must be a JSON object';
    }
    const allowedKeys = new Set(['required', 'properties']);
    const extraKeys = Object.keys(parsed).filter((k) => !allowedKeys.has(k));
    if (extraKeys.length > 0) {
      return `Only "required" and "properties" keys are allowed. Unexpected: ${extraKeys.join(', ')}`;
    }
    if ('required' in parsed && !Array.isArray(parsed.required)) {
      return '"required" must be an array of strings';
    }
    if ('properties' in parsed && (typeof parsed.properties !== 'object' || Array.isArray(parsed.properties))) {
      return '"properties" must be an object';
    }
    return undefined;
  } catch {
    return 'Invalid JSON — check for syntax errors';
  }
}

// ---------------------------------------------------------------------------
// TagInput — simple comma-separated / enter-to-add tag input
// ---------------------------------------------------------------------------

interface TagInputProps {
  value: string[];
  onChange: (value: string[]) => void;
  placeholder?: string;
  disabled?: boolean;
  id?: string;
}

function TagInput({ value, onChange, placeholder, disabled, id }: TagInputProps) {
  const [inputValue, setInputValue] = React.useState('');

  const addTag = React.useCallback(
    (raw: string) => {
      const tag = raw.trim();
      if (tag && !value.includes(tag)) {
        onChange([...value, tag]);
      }
      setInputValue('');
    },
    [value, onChange]
  );

  const removeTag = React.useCallback(
    (tag: string) => {
      onChange(value.filter((t) => t !== tag));
    },
    [value, onChange]
  );

  const handleKeyDown = React.useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag(inputValue);
      } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
        onChange(value.slice(0, -1));
      }
    },
    [inputValue, addTag, value, onChange]
  );

  return (
    <div className="space-y-2">
      <div className="flex min-h-9 flex-wrap gap-1 rounded-md border border-input bg-background px-3 py-1.5 focus-within:ring-1 focus-within:ring-ring">
        {value.map((tag) => (
          <Badge key={tag} variant="secondary" className="flex items-center gap-1 text-xs">
            {tag}
            {!disabled && (
              <button
                type="button"
                onClick={() => removeTag(tag)}
                aria-label={`Remove ${tag}`}
                className="ml-0.5 rounded hover:text-destructive focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </Badge>
        ))}
        {!disabled && (
          <input
            id={id}
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={() => inputValue && addTag(inputValue)}
            placeholder={value.length === 0 ? placeholder : ''}
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
        )}
      </div>
      {!disabled && (
        <p className="text-xs text-muted-foreground">Press Enter or comma to add a key</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Form state
// ---------------------------------------------------------------------------

interface FormState {
  slug: string;
  label: string;
  description: string;
  icon: string;
  color: string;
  path_prefix: string;
  required_frontmatter_keys: string[];
  example_path: string;
  content_template: string;
  applicable_platforms: string[];
  frontmatter_schema_text: string;
}

function buildInitialState(config: EntityTypeConfig | null): FormState {
  if (config) {
    return {
      slug: config.slug,
      label: config.display_name,
      description: config.description ?? '',
      icon: config.icon ?? '',
      color: config.color ?? '',
      path_prefix: config.path_prefix ?? '',
      required_frontmatter_keys: config.required_frontmatter_keys ?? [],
      example_path: '',
      content_template: config.content_template ?? '',
      applicable_platforms: config.applicable_platforms ?? [],
      frontmatter_schema_text: config.frontmatter_schema
        ? JSON.stringify(config.frontmatter_schema, null, 2)
        : '',
    };
  }
  return {
    slug: '',
    label: '',
    description: '',
    icon: '',
    color: '',
    path_prefix: '',
    required_frontmatter_keys: [],
    example_path: '',
    content_template: '',
    applicable_platforms: [],
    frontmatter_schema_text: '',
  };
}

// ---------------------------------------------------------------------------
// EntityTypeConfigForm
// ---------------------------------------------------------------------------

interface EntityTypeConfigFormProps {
  open: boolean;
  onClose: () => void;
  /** If provided, the form operates in edit mode */
  editingConfig: EntityTypeConfig | null;
}

/**
 * Dialog form for creating and editing entity type configurations.
 *
 * - Create mode: all fields editable, slug validated against ^[a-z][a-z0-9_]{0,63}$
 * - Edit mode (non-builtin): all fields editable except slug (locked)
 * - Edit mode (builtin): only content_template editable; all other fields read-only
 */
export function EntityTypeConfigForm({ open, onClose, editingConfig }: EntityTypeConfigFormProps) {
  const isEdit = editingConfig !== null;
  const isBuiltin = editingConfig?.is_builtin ?? false;

  const createConfig = useCreateEntityTypeConfig();
  const updateConfig = useUpdateEntityTypeConfig();
  const { toast } = useToast();

  const [form, setForm] = React.useState<FormState>(() => buildInitialState(editingConfig));
  const [slugError, setSlugError] = React.useState<string | undefined>();
  const [schemaError, setSchemaError] = React.useState<string | undefined>();
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Reinitialise form when the dialog opens with a different config
  React.useEffect(() => {
    if (open) {
      setForm(buildInitialState(editingConfig));
      setSlugError(undefined);
      setSchemaError(undefined);
    }
  }, [open, editingConfig]);

  const setField = React.useCallback(
    <K extends keyof FormState>(key: K, value: FormState[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const handleSlugChange = React.useCallback((value: string) => {
    setField('slug', value);
    setSlugError(validateSlug(value));
  }, [setField]);

  const handleSchemaBlur = React.useCallback(() => {
    setSchemaError(validateFrontmatterSchema(form.frontmatter_schema_text));
  }, [form.frontmatter_schema_text]);

  const handlePlatformToggle = React.useCallback((slug: string, checked: boolean) => {
    setForm((prev) => ({
      ...prev,
      applicable_platforms: checked
        ? [...prev.applicable_platforms, slug]
        : prev.applicable_platforms.filter((p) => p !== slug),
    }));
  }, []);

  const parseFrontmatterSchema = React.useCallback((): Record<string, unknown> | null => {
    const text = form.frontmatter_schema_text.trim();
    if (!text) return null;
    try {
      return JSON.parse(text) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [form.frontmatter_schema_text]);

  const handleSubmit = React.useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!isEdit) {
        const err = validateSlug(form.slug);
        if (err) {
          setSlugError(err);
          return;
        }
      }

      if (!form.label.trim()) return;

      // Validate schema before submit
      const schemaErr = validateFrontmatterSchema(form.frontmatter_schema_text);
      if (schemaErr) {
        setSchemaError(schemaErr);
        return;
      }

      setIsSubmitting(true);
      try {
        const parsedSchema = parseFrontmatterSchema();
        const applicablePlatforms =
          form.applicable_platforms.length > 0 ? form.applicable_platforms : null;

        if (isEdit && editingConfig) {
          const updateData: EntityTypeConfigUpdate = {
            label: form.label || undefined,
            description: form.description || undefined,
            icon: form.icon || undefined,
            color: form.color || null,
            path_prefix: form.path_prefix || undefined,
            required_frontmatter_keys:
              form.required_frontmatter_keys.length > 0
                ? form.required_frontmatter_keys
                : undefined,
            example_path: form.example_path || undefined,
            content_template: form.content_template || undefined,
            applicable_platforms: applicablePlatforms,
            frontmatter_schema: parsedSchema,
          };
          await updateConfig.mutateAsync({ slug: editingConfig.slug, data: updateData });
          toast({
            title: 'Entity type updated',
            description: `"${form.label}" has been updated.`,
          });
        } else {
          const createData: EntityTypeConfigCreate = {
            slug: form.slug,
            label: form.label,
            description: form.description || undefined,
            icon: form.icon || undefined,
            color: form.color || null,
            path_prefix: form.path_prefix || undefined,
            required_frontmatter_keys:
              form.required_frontmatter_keys.length > 0
                ? form.required_frontmatter_keys
                : undefined,
            example_path: form.example_path || undefined,
            content_template: form.content_template || undefined,
            applicable_platforms: applicablePlatforms,
            frontmatter_schema: parsedSchema,
          };
          await createConfig.mutateAsync(createData);
          toast({
            title: 'Entity type created',
            description: `"${form.label}" has been added.`,
          });
        }
        onClose();
      } catch (err) {
        toast({
          title: isEdit ? 'Update failed' : 'Create failed',
          description: err instanceof Error ? err.message : 'An error occurred',
          variant: 'destructive',
        });
      } finally {
        setIsSubmitting(false);
      }
    },
    [form, isEdit, editingConfig, createConfig, updateConfig, toast, onClose, parseFrontmatterSchema]
  );

  const dialogTitle = isEdit
    ? `Edit ${isBuiltin ? '(Built-in) ' : ''}${editingConfig?.display_name ?? 'Entity Type'}`
    : 'Add Entity Type';

  const dialogDescription = isBuiltin
    ? 'Built-in types are read-only. Only the content template can be modified.'
    : isEdit
    ? 'Update the entity type configuration. The slug cannot be changed.'
    : 'Define a new custom entity type configuration. The slug uniquely identifies this type.';

  // For built-in types in edit mode, only content_template is editable
  const fieldsReadOnly = isBuiltin;
  // Slug is always read-only in edit mode
  const slugReadOnly = isEdit;

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-h-[90vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{dialogTitle}</DialogTitle>
          <DialogDescription>{dialogDescription}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5" aria-label={dialogTitle}>
          {/* Slug — create only */}
          <div className="space-y-1.5">
            <Label htmlFor="etc-slug">
              Slug <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="etc-slug"
              value={form.slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              placeholder="e.g. my_entity_type"
              disabled={slugReadOnly}
              aria-describedby={slugError ? 'etc-slug-error' : 'etc-slug-hint'}
              aria-invalid={!!slugError}
            />
            {slugError ? (
              <p id="etc-slug-error" className="text-xs text-destructive" role="alert">
                {slugError}
              </p>
            ) : (
              <p id="etc-slug-hint" className="text-xs text-muted-foreground">
                Must start with a lowercase letter; only lowercase letters, digits, and underscores
                (max 64 chars).
              </p>
            )}
          </div>

          {/* Label */}
          <div className="space-y-1.5">
            <Label htmlFor="etc-label">
              Display Name <span aria-hidden="true" className="text-destructive">*</span>
            </Label>
            <Input
              id="etc-label"
              value={form.label}
              onChange={(e) => setField('label', e.target.value)}
              placeholder="e.g. My Entity Type"
              disabled={fieldsReadOnly}
              required
            />
          </div>

          {/* Description */}
          <div className="space-y-1.5">
            <Label htmlFor="etc-description">Description</Label>
            <Textarea
              id="etc-description"
              value={form.description}
              onChange={(e) => setField('description', e.target.value)}
              placeholder="Describe the purpose of this entity type…"
              rows={2}
              disabled={fieldsReadOnly}
            />
          </div>

          {/* Icon + Path prefix — side by side */}
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label htmlFor="etc-icon">Icon</Label>
              <IconPicker
                value={form.icon}
                onChange={(iconName) => setField('icon', iconName)}
                disabled={fieldsReadOnly}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="etc-path-prefix">Path Prefix</Label>
              <Input
                id="etc-path-prefix"
                value={form.path_prefix}
                onChange={(e) => setField('path_prefix', e.target.value)}
                placeholder="e.g. .claude/skills"
                disabled={fieldsReadOnly}
              />
            </div>
          </div>

          {/* Color */}
          {!isBuiltin && (
            <div className="space-y-2">
              <Label>Color</Label>
              <ColorSelector
                value={form.color || '#3B82F6'}
                onChange={(hex) => setField('color', hex)}
                disabled={fieldsReadOnly}
              />
              <p className="text-xs text-muted-foreground">
                Color for entity type indicators on cards. Leave at default to use the built-in palette.
              </p>
            </div>
          )}

          {/* Required frontmatter keys */}
          <div className="space-y-1.5">
            <Label htmlFor="etc-frontmatter-keys">Required Frontmatter Keys</Label>
            <TagInput
              id="etc-frontmatter-keys"
              value={form.required_frontmatter_keys}
              onChange={(v) => setField('required_frontmatter_keys', v)}
              placeholder="Add a key and press Enter…"
              disabled={fieldsReadOnly}
            />
          </div>

          {/* Example path */}
          <div className="space-y-1.5">
            <Label htmlFor="etc-example-path">Example Path</Label>
            <Input
              id="etc-example-path"
              value={form.example_path}
              onChange={(e) => setField('example_path', e.target.value)}
              placeholder="e.g. .claude/skills/my-skill.md"
              disabled={fieldsReadOnly}
            />
          </div>

          {/* Applicable Platforms — hidden for built-in types */}
          {!isBuiltin && (
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium leading-none">Applicable Platforms</legend>
              <p id="etc-platforms-hint" className="text-xs text-muted-foreground">
                Leave empty to apply to all platforms.
              </p>
              <div
                className="flex flex-wrap gap-x-6 gap-y-2 pt-1"
                role="group"
                aria-describedby="etc-platforms-hint"
                aria-label="Applicable platforms"
              >
                {APPLICABLE_PLATFORMS.map(({ slug, label }) => {
                  const checkboxId = `etc-platform-${slug}`;
                  const isChecked = form.applicable_platforms.includes(slug);
                  return (
                    <div key={slug} className="flex items-center gap-2">
                      <Checkbox
                        id={checkboxId}
                        checked={isChecked}
                        onCheckedChange={(checked) =>
                          handlePlatformToggle(slug, checked === true)
                        }
                        aria-label={label}
                      />
                      <Label htmlFor={checkboxId} className="cursor-pointer font-normal">
                        {label}
                      </Label>
                    </div>
                  );
                })}
              </div>
            </fieldset>
          )}

          {/* Frontmatter Schema — hidden for built-in types */}
          {!isBuiltin && (
            <div className="space-y-1.5">
              <Label htmlFor="etc-frontmatter-schema">Frontmatter Schema (JSON)</Label>
              <Textarea
                id="etc-frontmatter-schema"
                value={form.frontmatter_schema_text}
                onChange={(e) => {
                  setField('frontmatter_schema_text', e.target.value);
                  // Clear error while user is editing
                  if (schemaError) setSchemaError(undefined);
                }}
                onBlur={handleSchemaBlur}
                placeholder={'{\n  "required": ["key1"],\n  "properties": {\n    "key1": { "type": "string" }\n  }\n}'}
                rows={6}
                className="font-mono text-sm"
                aria-describedby={schemaError ? 'etc-schema-error' : 'etc-schema-hint'}
                aria-invalid={!!schemaError}
              />
              {schemaError ? (
                <p id="etc-schema-error" className="text-xs text-destructive" role="alert">
                  {schemaError}
                </p>
              ) : (
                <p id="etc-schema-hint" className="text-xs text-muted-foreground">
                  Optional JSON Schema subset for frontmatter validation. Supported keys:{' '}
                  <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">required</code>{' '}
                  (array of strings) and{' '}
                  <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">properties</code>{' '}
                  (map of key to type descriptor, e.g.{' '}
                  <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">
                    {`{"type": "string"}`}
                  </code>
                  ).
                </p>
              )}
            </div>
          )}

          {/* Content template */}
          <div className="space-y-1.5">
            <Label htmlFor="etc-content-template">Content Template</Label>
            <Textarea
              id="etc-content-template"
              value={form.content_template}
              onChange={(e) => setField('content_template', e.target.value)}
              placeholder="# {{name}}\n\nDefault content for new entities of this type…"
              rows={8}
              className="font-mono text-sm"
              // content_template is always editable (even for built-in types)
            />
            <p className="text-xs text-muted-foreground">
              Markdown template pre-populated when creating a new entity of this type.
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || (!isEdit && !!slugError) || !!schemaError}>
              {isSubmitting ? 'Saving…' : isEdit ? 'Save Changes' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
