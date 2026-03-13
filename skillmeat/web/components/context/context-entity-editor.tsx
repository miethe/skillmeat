'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { Loader2, Info, X, ChevronDown, Check, HelpCircle } from 'lucide-react';
import {
  ContextEntity,
  CreateContextEntityRequest,
  UpdateContextEntityRequest,
  ContextEntityType,
  EntityTypeConfig,
} from '@/types/context-entity';
import { Platform } from '@/types/enums';
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
import { Badge } from '@/components/ui/badge';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import { MarkdownEditor } from '@skillmeat/content-viewer';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  useCreateContextEntity,
  useUpdateContextEntity,
  useContextEntityContent,
  useEntityTypeConfigs,
  useEntityCategories,
  useCreateEntityCategory,
  type EntityCategory,
} from '@/hooks';

// ============================================================================
// Feature flag — set to `true` to enable the enhanced v2 creation form.
// In production wire this to `useFeatureFlags()` when the backend exposes it.
// ============================================================================
const CREATION_FORM_V2 =
  process.env.NEXT_PUBLIC_CREATION_FORM_V2 === 'true' ||
  process.env.NODE_ENV === 'development';

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
  /** Whether the editor dialog is open */
  open: boolean;
  /** Callback when dialog should close */
  onClose: () => void;
  /** Callback when entity is successfully created/updated */
  onSuccess: () => void;
  /** Whether save operation is in progress */
  isLoading?: boolean;
}

interface FormData {
  name: string;
  entity_type: ContextEntityType;
  path_pattern: string;
  description?: string;
  auto_load: boolean;
  version?: string;
  content: string;
}

/**
 * Entity type options for select dropdown (legacy v1 form fallback)
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

// ============================================================================
// Platform multi-select constants
// ============================================================================

interface PlatformOption {
  value: string;
  label: string;
  rootDir: string;
}

/** Ordered list of supported platforms for the multi-select */
const PLATFORM_OPTIONS: PlatformOption[] = [
  { value: Platform.CLAUDE_CODE, label: 'Claude Code', rootDir: '.claude' },
  { value: Platform.CURSOR, label: 'Cursor', rootDir: '.cursor' },
  { value: Platform.CODEX, label: 'Codex', rootDir: '.codex' },
  { value: Platform.GEMINI, label: 'Gemini', rootDir: '.gemini' },
  { value: 'windsurf', label: 'Windsurf', rootDir: '.windsurf' },
  { value: 'cline', label: 'Cline', rootDir: '.cline' },
  { value: 'roo-code', label: 'Roo Code', rootDir: '.roo' },
  { value: Platform.OTHER, label: 'Generic / Other', rootDir: '.custom' },
];

/**
 * Filter PLATFORM_OPTIONS to only those allowed by the entity type config.
 * When applicable_platforms is null, all platforms are allowed.
 */
function getFilteredPlatformOptions(config: EntityTypeConfig | null): PlatformOption[] {
  if (!config || config.applicable_platforms === null) {
    return PLATFORM_OPTIONS;
  }
  return PLATFORM_OPTIONS.filter((p) => config.applicable_platforms!.includes(p.value));
}

/**
 * Extract required frontmatter keys from a JSON Schema subset.
 * Supports the standard `required` array at the top level of the schema.
 */
function extractSchemaRequiredKeys(schema: Record<string, unknown> | null): string[] {
  if (!schema) return [];
  const required = schema['required'];
  if (Array.isArray(required)) {
    return required.filter((k): k is string => typeof k === 'string');
  }
  return [];
}

/** Derive a suggested path from entity type config + first selected platform */
function derivePathPattern(config: EntityTypeConfig | null, platforms: string[]): string {
  if (!config) return '.claude/';

  // For custom types with no path_prefix set, leave the path field empty
  if (!config.is_builtin && !config.path_prefix) {
    return '';
  }

  const prefix = config.path_prefix?.replace(/\/$/, '') || '.claude';

  // Support {PLATFORM} token in path_prefix — always keep token visible to indicate dynamic path
  if (prefix.includes('{PLATFORM}')) {
    if (platforms.length === 0) {
      // Strip the token placeholder gracefully when no platform selected
      return `${prefix.replace(/\/?\{PLATFORM\}/g, '')}/`;
    }
    // Always show parameterized pattern with {PLATFORM} token
    return `${prefix}/`;
  }

  if (platforms.length === 0) {
    return `${prefix}/`;
  }

  // Always show parameterized pattern so users see the {PLATFORM} token
  // Derive the sub-path after the root dir (e.g. "rules" from ".claude/rules")
  const prefixParts = prefix.split('/');
  const subPath = prefixParts.length > 1 ? prefixParts.slice(1).join('/') : null;
  if (subPath) {
    return `{PLATFORM}/${subPath}/`;
  }

  return `{PLATFORM}/`;
}

/**
 * For a given config and platform list, compute the resolved path prefix per platform.
 * Used to populate the tooltip breakdown when multiple platforms are selected.
 */
function resolvePerPlatformPaths(
  config: EntityTypeConfig | null,
  platforms: string[],
): Array<{ label: string; path: string }> {
  if (!config || platforms.length === 0) return [];

  const prefix = config.path_prefix?.replace(/\/$/, '') || '.claude';

  return platforms.flatMap((platform) => {
    const platformOpt = PLATFORM_OPTIONS.find((p) => p.value === platform);
    if (!platformOpt) return [];

    let resolvedPath: string;
    if (prefix.includes('{PLATFORM}')) {
      resolvedPath = `${prefix.replace('{PLATFORM}', platform)}/`;
    } else {
      const prefixParts = prefix.split('/');
      if (prefixParts.length > 1) {
        const parts = [...prefixParts];
        parts[0] = platformOpt.rootDir;
        resolvedPath = `${parts.join('/')}/`;
      } else {
        resolvedPath = `${platformOpt.rootDir}/`;
      }
    }

    return [{ label: platformOpt.label, path: resolvedPath }];
  });
}

// ============================================================================
// Sub-components
// ============================================================================

/** Platform multi-select built on Popover + Command */
interface PlatformMultiSelectProps {
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
  /** Restrict visible platform options. Defaults to all PLATFORM_OPTIONS when not provided. */
  availableOptions?: PlatformOption[];
  /** id for the trigger button, used to associate with a <Label htmlFor> */
  id?: string;
  /** aria-describedby for the trigger button */
  'aria-describedby'?: string;
}

function PlatformMultiSelect({ value, onChange, disabled, availableOptions, id, 'aria-describedby': ariaDescribedby }: PlatformMultiSelectProps) {
  const [open, setOpen] = useState(false);

  const options = availableOptions ?? PLATFORM_OPTIONS;

  const toggle = (platform: string) => {
    if (value.includes(platform)) {
      onChange(value.filter((v) => v !== platform));
    } else {
      onChange([...value, platform]);
    }
  };

  const removeChip = (platform: string, e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(value.filter((v) => v !== platform));
  };

  const selectedEntries = value.map((v) => ({
    value: v,
    label: PLATFORM_OPTIONS.find((p) => p.value === v)?.label ?? v,
  }));

  const listboxId = `${id ?? 'platform-multiselect'}-listbox`;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <div
          id={id}
          role="combobox"
          tabIndex={disabled ? -1 : 0}
          aria-expanded={open}
          aria-label={value.length === 0 ? 'Select platforms' : `${value.length} platform${value.length === 1 ? '' : 's'} selected`}
          aria-haspopup="listbox"
          aria-controls={open ? listboxId : undefined}
          aria-describedby={ariaDescribedby}
          aria-disabled={disabled}
          onClick={() => !disabled && setOpen(!open)}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setOpen(!open);
            }
          }}
          className={[
            'flex min-h-9 w-full cursor-pointer flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
            disabled ? 'cursor-not-allowed opacity-50' : '',
          ].filter(Boolean).join(' ')}
        >
          {selectedEntries.length === 0 ? (
            <span className="text-muted-foreground">Select platforms…</span>
          ) : (
            selectedEntries.map(({ value: v, label }) => (
              <Badge key={v} variant="secondary" className="gap-0.5 pr-1 text-xs">
                {label}
                <button
                  type="button"
                  aria-label={`Remove ${label}`}
                  onClick={(e) => removeChip(v, e)}
                  className="ml-0.5 rounded-full hover:bg-destructive/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))
          )}
          <ChevronDown className="ml-auto h-4 w-4 shrink-0 text-muted-foreground" />
        </div>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-0" align="start">
        <Command>
          <CommandInput placeholder="Search platforms…" aria-label="Search platforms" />
          <CommandList id={listboxId} role="listbox" aria-label="Available platforms" aria-multiselectable="true">
            <CommandEmpty>No platform found.</CommandEmpty>
            <CommandGroup>
              {options.map((platform) => {
                const selected = value.includes(platform.value);
                return (
                  <CommandItem
                    key={platform.value}
                    value={platform.value}
                    onSelect={() => toggle(platform.value)}
                    role="option"
                    aria-selected={selected}
                  >
                    <Check
                      className={['mr-2 h-4 w-4', selected ? 'opacity-100' : 'opacity-0'].join(
                        ' '
                      )}
                      aria-hidden="true"
                    />
                    <span>{platform.label}</span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {platform.rootDir}
                    </span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// ============================================================================
// Category multi-select with inline create
// ============================================================================

interface CategoryMultiSelectProps {
  value: number[];
  onChange: (value: number[]) => void;
  disabled?: boolean;
  /** id for the trigger button, used to associate with a <Label htmlFor> */
  id?: string;
  /** aria-describedby for the trigger button */
  'aria-describedby'?: string;
}

function CategoryMultiSelect({ value, onChange, disabled, id, 'aria-describedby': ariaDescribedby }: CategoryMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');

  const { data: categories = [] } = useEntityCategories();
  const createCategory = useCreateEntityCategory();

  const selectedCategories = value.map((id) => categories.find((c) => c.id === id)).filter(
    (c): c is EntityCategory => c !== undefined
  );

  const toggle = (id: number) => {
    if (value.includes(id)) {
      onChange(value.filter((v) => v !== id));
    } else {
      onChange([...value, id]);
    }
  };

  const removeChip = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(value.filter((v) => v !== id));
  };

  const filteredCategories = categories.filter((c) =>
    c.name.toLowerCase().includes(inputValue.toLowerCase())
  );

  const exactMatch = categories.some(
    (c) => c.name.toLowerCase() === inputValue.toLowerCase()
  );

  const handleKeyDown = async (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && inputValue.trim() && !exactMatch) {
      e.preventDefault();
      e.stopPropagation();
      try {
        const newCategory = await createCategory.mutateAsync({ name: inputValue.trim() });
        onChange([...value, newCategory.id]);
        setInputValue('');
      } catch {
        // Ignore — error will surface via the mutation state if needed
      }
    }
  };

  const listboxId = `${id ?? 'category-multiselect'}-listbox`;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <div
          id={id}
          role="combobox"
          tabIndex={disabled ? -1 : 0}
          aria-expanded={open}
          aria-label={value.length === 0 ? 'Select categories' : `${value.length} categor${value.length === 1 ? 'y' : 'ies'} selected`}
          aria-haspopup="listbox"
          aria-controls={open ? listboxId : undefined}
          aria-describedby={ariaDescribedby}
          aria-disabled={disabled}
          onClick={() => !disabled && setOpen(!open)}
          onKeyDown={(e) => {
            if (disabled) return;
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setOpen(!open);
            }
          }}
          className={[
            'flex min-h-9 w-full cursor-pointer flex-wrap items-center gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
            disabled ? 'cursor-not-allowed opacity-50' : '',
          ].filter(Boolean).join(' ')}
        >
          {selectedCategories.length === 0 ? (
            <span className="text-muted-foreground">Select or create categories…</span>
          ) : (
            selectedCategories.map((cat) => (
              <Badge
                key={cat.id}
                variant="secondary"
                className="gap-0.5 pr-1 text-xs"
                style={cat.color ? { backgroundColor: `${cat.color}20`, borderColor: cat.color } : undefined}
              >
                {cat.name}
                <button
                  type="button"
                  aria-label={`Remove ${cat.name}`}
                  onClick={(e) => removeChip(cat.id, e)}
                  className="ml-0.5 rounded-full hover:bg-destructive/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            ))
          )}
          <ChevronDown className="ml-auto h-4 w-4 shrink-0 text-muted-foreground" />
        </div>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-0" align="start">
        <Command>
          <CommandInput
            placeholder="Search or create category…"
            aria-label="Search or create category"
            value={inputValue}
            onValueChange={setInputValue}
            onKeyDown={handleKeyDown}
          />
          <CommandList id={listboxId} role="listbox" aria-label="Available categories" aria-multiselectable="true">
            {filteredCategories.length === 0 && !inputValue && (
              <CommandEmpty>No categories yet. Type to create one.</CommandEmpty>
            )}
            {filteredCategories.length === 0 && inputValue && (
              <CommandEmpty>
                {createCategory.isPending ? (
                  <span className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Creating &ldquo;{inputValue}&rdquo;…
                  </span>
                ) : (
                  <span className="text-xs text-muted-foreground">
                    Press Enter to create &ldquo;{inputValue}&rdquo;
                  </span>
                )}
              </CommandEmpty>
            )}
            {filteredCategories.length > 0 && (
              <CommandGroup>
                {filteredCategories.map((cat) => {
                  const selected = value.includes(cat.id);
                  return (
                    <CommandItem
                      key={cat.id}
                      value={cat.name}
                      onSelect={() => toggle(cat.id)}
                      role="option"
                      aria-selected={selected}
                    >
                      <Check
                        className={['mr-2 h-4 w-4', selected ? 'opacity-100' : 'opacity-0'].join(' ')}
                        aria-hidden="true"
                      />
                      <span>{cat.name}</span>
                      {cat.color && (
                        <span
                          className="ml-auto h-3 w-3 rounded-full border"
                          style={{ backgroundColor: cat.color }}
                          aria-hidden="true"
                        />
                      )}
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            )}
            {inputValue && !exactMatch && filteredCategories.length > 0 && (
              <CommandGroup>
                <CommandItem
                  value={`__create__${inputValue}`}
                  onSelect={async () => {
                    try {
                      const newCategory = await createCategory.mutateAsync({ name: inputValue.trim() });
                      onChange([...value, newCategory.id]);
                      setInputValue('');
                    } catch {
                      // Ignore
                    }
                  }}
                  disabled={createCategory.isPending}
                >
                  {createCategory.isPending ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <span className="mr-2 text-xs font-medium text-muted-foreground">+</span>
                  )}
                  <span className="text-sm">
                    Create &ldquo;{inputValue}&rdquo;
                  </span>
                </CommandItem>
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

/** Inline validation hints panel — shows required frontmatter keys + description */
interface EntityTypeHintsPanelProps {
  config: EntityTypeConfig | null;
  id: string;
}

function EntityTypeHintsPanel({ config, id }: EntityTypeHintsPanelProps) {
  if (!config) return null;

  // Merge required_frontmatter_keys + frontmatter_schema.required (deduplicated)
  const explicitKeys = config.required_frontmatter_keys ?? [];
  const schemaKeys = extractSchemaRequiredKeys(config.frontmatter_schema);
  const requiredKeys = Array.from(new Set([...explicitKeys, ...schemaKeys]));

  const hasRequiredKeys = requiredKeys.length > 0;
  const hasDescription = !!config.description;
  const isCustomType = !config.is_builtin;

  if (!hasRequiredKeys && !hasDescription && !isCustomType) return null;

  return (
    <div
      id={id}
      role="note"
      className="flex items-start gap-2 rounded-md border border-blue-200 bg-blue-50 p-2.5 dark:border-blue-800/50 dark:bg-blue-950/30"
    >
      <Info
        className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-500 dark:text-blue-400"
        aria-hidden="true"
      />
      <div className="min-w-0 space-y-1">
        {hasDescription && (
          <p className="text-xs text-blue-700 dark:text-blue-300">{config.description}</p>
        )}
        {hasRequiredKeys && (
          <div>
            <p className="mb-1 text-xs font-medium text-blue-700 dark:text-blue-300">
              Required frontmatter:
            </p>
            <div className="flex flex-wrap gap-1">
              {requiredKeys.map((key) => (
                <code
                  key={key}
                  className="rounded bg-blue-100 px-1 py-0.5 text-xs font-mono text-blue-800 dark:bg-blue-900/50 dark:text-blue-200"
                >
                  {key}
                </code>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// V2 Enhanced form (inner — reuses same form setup as outer component)
// ============================================================================

interface V2FormFieldsProps {
  control: ReturnType<typeof useForm<FormData>>['control'];
  register: ReturnType<typeof useForm<FormData>>['register'];
  errors: ReturnType<typeof useForm<FormData>>['formState']['errors'];
  isLoading: boolean;
  // V2-specific
  entityTypeConfigs: EntityTypeConfig[];
  selectedConfig: EntityTypeConfig | null;
  onEntityTypeChange: (type: string) => void;
  platforms: string[];
  onPlatformsChange: (platforms: string[]) => void;
  pathPatternDerived: boolean;
  onPathPatternEdit: () => void;
  selectedCategoryIds: number[];
  onCategoryIdsChange: (ids: number[]) => void;
  /** Filtered platform options based on the selected entity type's applicable_platforms */
  availablePlatformOptions: PlatformOption[];
}

function V2FormFields({
  control,
  register,
  errors,
  isLoading,
  entityTypeConfigs,
  selectedConfig,
  onEntityTypeChange,
  platforms,
  onPlatformsChange,
  pathPatternDerived,
  onPathPatternEdit,
  selectedCategoryIds,
  onCategoryIdsChange,
  availablePlatformOptions,
}: V2FormFieldsProps) {
  const hintsPanelId = 'entity-type-hints';

  return (
    <>
      {/* Name field */}
      <div className="space-y-2">
        <Label htmlFor="name">
          Name <span className="text-destructive" aria-hidden="true">*</span>
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
          aria-required="true"
          aria-invalid={!!errors.name}
          aria-describedby={errors.name ? 'name-error' : undefined}
        />
        {errors.name && (
          <p id="name-error" className="text-sm text-destructive" role="alert">
            {errors.name.message}
          </p>
        )}
      </div>

      {/* Entity type field — v2 uses dynamic configs from API */}
      <div className="space-y-2">
        <Label htmlFor="entity_type">
          Entity Type <span className="text-destructive" aria-hidden="true">*</span>
        </Label>
        <Controller
          name="entity_type"
          control={control}
          rules={{ required: 'Entity type is required' }}
          render={({ field: { value } }) => (
            <Select
              value={value}
              onValueChange={onEntityTypeChange}
              disabled={isLoading}
            >
              <SelectTrigger
                id="entity_type"
                aria-required="true"
                aria-invalid={!!errors.entity_type}
                aria-describedby={
                  [errors.entity_type ? 'entity-type-error' : '', hintsPanelId]
                    .filter(Boolean)
                    .join(' ') || undefined
                }
                className="[&_[data-description]]:hidden"
              >
                <SelectValue placeholder="Select entity type…" />
              </SelectTrigger>
              <SelectContent>
                {/* Built-in types first, then custom types */}
                {[
                  ...entityTypeConfigs.filter((c) => c.is_builtin),
                  ...entityTypeConfigs.filter((c) => !c.is_builtin),
                ].map((cfg) => (
                  <SelectItem key={cfg.slug} value={cfg.slug}>
                    <div className="flex items-start gap-2">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium">{cfg.display_name}</span>
                          {!cfg.is_builtin && (
                            <Badge
                              variant="outline"
                              className="h-4 shrink-0 px-1 py-0 text-[10px] font-normal text-muted-foreground"
                            >
                              custom
                            </Badge>
                          )}
                        </div>
                        {cfg.description && (
                          <div data-description className="text-xs text-muted-foreground">{cfg.description}</div>
                        )}
                      </div>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.entity_type && (
          <p id="entity-type-error" className="text-sm text-destructive" role="alert">
            {errors.entity_type.message}
          </p>
        )}
        {/* Inline validation hints */}
        <EntityTypeHintsPanel config={selectedConfig} id={hintsPanelId} />
      </div>

      {/* Platform multi-select */}
      <div className="space-y-2">
        <Label htmlFor="platforms">Target Platforms</Label>
        <PlatformMultiSelect
          id="platforms"
          value={platforms}
          onChange={onPlatformsChange}
          disabled={isLoading}
          availableOptions={availablePlatformOptions}
          aria-describedby="platforms-help"
        />
        <p id="platforms-help" className="text-xs text-muted-foreground">
          {availablePlatformOptions.length < PLATFORM_OPTIONS.length
            ? `This type supports ${availablePlatformOptions.length} platform${availablePlatformOptions.length === 1 ? '' : 's'}. Restricts deployment to selected platforms.`
            : 'Optional. Restricts deployment to selected platforms.'}
        </p>
      </div>

      {/* Path pattern — auto-derived or manual */}
      {(() => {
        const perPlatformPaths = resolvePerPlatformPaths(selectedConfig, platforms);
        const isMultiPlatform = platforms.length > 1;
        // Build dynamic example based on selected entity type and first platform
        const firstPlatformOpt = platforms.length > 0
          ? PLATFORM_OPTIONS.find((p) => p.value === platforms[0])
          : null;
        const exampleRoot = firstPlatformOpt?.rootDir ?? '.claude';
        const exampleSubPath = selectedConfig?.path_prefix
          ? selectedConfig.path_prefix.replace(/\/$/, '').split('/').slice(1).join('/')
          : 'context';
        const examplePath = exampleSubPath
          ? `${exampleRoot}/${exampleSubPath}/my-entity.md`
          : `${exampleRoot}/context/my-entity.md`;

        return (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="path_pattern">
                Path Pattern <span className="text-destructive" aria-hidden="true">*</span>
              </Label>
              {pathPatternDerived && (
                <span className="text-xs text-muted-foreground italic">auto-derived</span>
              )}
            </div>
            <div className="relative">
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
                aria-required="true"
                aria-invalid={!!errors.path_pattern}
                aria-describedby={errors.path_pattern ? 'path-pattern-error path_pattern-help' : 'path_pattern-help'}
                className={perPlatformPaths.length > 0 ? 'pr-8' : undefined}
                onChange={(e) => {
                  // Detect manual edit — mark as no longer auto-derived
                  onPathPatternEdit();
                  // Let react-hook-form handle the value update via register's onChange
                  register('path_pattern').onChange(e);
                }}
              />
              {perPlatformPaths.length > 0 && (
                <TooltipProvider>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        type="button"
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                        aria-label="View per-platform resolved paths"
                        tabIndex={0}
                      >
                        <HelpCircle className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="top" align="end" className="max-w-xs">
                      <p className="mb-1.5 text-xs font-medium">Resolved per platform:</p>
                      <ul className="space-y-1" role="list">
                        {perPlatformPaths.map(({ label, path }) => (
                          <li key={label} className="flex items-baseline gap-1.5" role="listitem">
                            <span className="shrink-0 text-xs font-medium">{label}:</span>
                            <code className="break-all text-xs">{path}</code>
                          </li>
                        ))}
                      </ul>
                    </TooltipContent>
                  </Tooltip>
                </TooltipProvider>
              )}
            </div>
            <p id="path_pattern-help" className="text-xs text-muted-foreground">
              {perPlatformPaths.length > 0
                ? <>
                    {isMultiPlatform ? 'Pattern applies across platforms.' : 'Path is resolved per platform.'}{' '}
                    Hover the <HelpCircle className="inline h-3 w-3 align-middle" aria-hidden="true" /> icon to see the resolved path{isMultiPlatform ? 's' : ''}.
                  </>
                : <>
                    Example:{' '}
                    <code className="rounded bg-muted px-1 py-0.5">{examplePath}</code>
                    {pathPatternDerived && '. Edit to override the auto-derived value.'}
                  </>
              }
            </p>
            {errors.path_pattern && (
              <p id="path-pattern-error" className="text-sm text-destructive" role="alert">
                {errors.path_pattern.message}
              </p>
            )}
          </div>
        );
      })()}

      {/* Description field */}
      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          {...register('description')}
          placeholder="Detailed description of this context entity…"
          rows={3}
          disabled={isLoading}
        />
      </div>

      {/* Category multi-select */}
      <div className="space-y-2">
        <Label htmlFor="categories">Categories</Label>
        <CategoryMultiSelect
          id="categories"
          value={selectedCategoryIds}
          onChange={onCategoryIdsChange}
          disabled={isLoading}
          aria-describedby="category-help"
        />
        <p id="category-help" className="text-xs text-muted-foreground">
          For progressive disclosure grouping. Type a new name and press Enter to create.
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
        <p id="version-help" className="text-xs text-muted-foreground">
          Semantic versioning recommended
        </p>
      </div>
    </>
  );
}

// ============================================================================
// Built-in fallback configs when the API is unavailable
// ============================================================================

const BUILTIN_ENTITY_TYPE_CONFIGS: EntityTypeConfig[] = [
  {
    id: 1,
    slug: 'project_config',
    display_name: 'Project Config',
    description: 'Configuration files (e.g., .claude/config.toml)',
    path_prefix: '.claude',
    is_builtin: true,
    sort_order: 0,
    created_at: '',
    updated_at: '',
    applicable_platforms: null,
    frontmatter_schema: null,
  },
  {
    id: 2,
    slug: 'spec_file',
    display_name: 'Spec File',
    description: 'Specification documents (e.g., .claude/specs/*.md)',
    path_prefix: '.claude/specs',
    is_builtin: true,
    sort_order: 1,
    created_at: '',
    updated_at: '',
    applicable_platforms: null,
    frontmatter_schema: null,
  },
  {
    id: 3,
    slug: 'rule_file',
    display_name: 'Rule File',
    description: 'Path-scoped rules (e.g., .claude/rules/web/*.md)',
    path_prefix: '.claude/rules',
    is_builtin: true,
    sort_order: 2,
    created_at: '',
    updated_at: '',
    applicable_platforms: null,
    frontmatter_schema: null,
  },
  {
    id: 4,
    slug: 'context_file',
    display_name: 'Context File',
    description: 'Knowledge documents (e.g., .claude/context/*.md)',
    path_prefix: '.claude/context',
    is_builtin: true,
    sort_order: 3,
    created_at: '',
    updated_at: '',
    applicable_platforms: null,
    frontmatter_schema: null,
  },
  {
    id: 5,
    slug: 'progress_template',
    display_name: 'Progress Template',
    description: 'Progress tracking templates',
    path_prefix: '.claude/progress',
    is_builtin: true,
    sort_order: 4,
    created_at: '',
    updated_at: '',
    applicable_platforms: null,
    frontmatter_schema: null,
  },
];

// ============================================================================
// Main editor component
// ============================================================================

/**
 * ContextEntityEditor - Create or edit context entity form in a modal dialog
 *
 * Renders the legacy v1 form when `CREATION_FORM_V2` is false, or the enhanced
 * v2 form otherwise. The v2 form adds:
 * - Platform multi-select with badge chips
 * - Auto-derived path pattern from entity type config + platform
 * - Content template injection on type selection
 * - Inline validation hints panel (required frontmatter keys)
 * - Graceful API fallback for entity type configs
 *
 * Features (both versions):
 * - Modal dialog wrapper
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
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   onSuccess={() => handleSuccess()}
 * />
 *
 * // Edit mode
 * <ContextEntityEditor
 *   entity={existingEntity}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   onSuccess={() => handleSuccess()}
 * />
 * ```
 */
export function ContextEntityEditor({
  entity,
  initialContent = '',
  open,
  onClose,
  onSuccess,
  isLoading: externalIsLoading = false,
}: ContextEntityEditorProps) {
  const [markdownContent, setMarkdownContent] = useState<string>(initialContent);
  const [contentInitialized, setContentInitialized] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // V2-specific state
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState<number[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<EntityTypeConfig | null>(null);
  const [pathPatternDerived, setPathPatternDerived] = useState(false);
  // Track whether the user has manually edited content (to avoid overwriting on template inject)
  const contentManuallyEdited = useRef(false);
  // Track the previous type's template so we can detect unedited template content on type switch
  const previousTemplateRef = useRef<string>('');

  // Determine if we're in edit mode
  const isEditMode = !!entity;

  // Fetch actual content when editing an existing entity
  const { data: fetchedContent, isLoading: isContentLoading } = useContextEntityContent(
    open && isEditMode ? entity?.id : undefined
  );

  // Entity type configs from API (v2 only — fetch regardless to avoid conditional hook)
  const { data: entityTypeConfigsData } = useEntityTypeConfigs();
  const entityTypeConfigs: EntityTypeConfig[] =
    entityTypeConfigsData && entityTypeConfigsData.length > 0
      ? entityTypeConfigsData
      : BUILTIN_ENTITY_TYPE_CONFIGS;

  // Mutations
  const createEntity = useCreateContextEntity();
  const updateEntity = useUpdateContextEntity();
  const isLoading =
    externalIsLoading || createEntity.isPending || updateEntity.isPending || isContentLoading;

  // Form setup with react-hook-form
  const {
    register,
    handleSubmit,
    formState: { errors },
    control,
    setValue,
    watch,
  } = useForm<FormData>({
    defaultValues: {
      name: entity?.name || '',
      entity_type: entity?.entity_type || 'context_file',
      path_pattern: entity?.path_pattern || '.claude/',
      description: entity?.description || '',
      auto_load: entity?.auto_load || false,
      version: entity?.version || '',
      content: initialContent,
    },
  });

  const watchedEntityType = watch('entity_type');

  // Initialize markdown content from fetched content once available
  useEffect(() => {
    if (fetchedContent && !contentInitialized) {
      setMarkdownContent(fetchedContent);
      setContentInitialized(true);
    }
  }, [fetchedContent, contentInitialized]);

  // Reset initialization flag + v2 state when dialog closes or entity changes
  useEffect(() => {
    if (!open) {
      setContentInitialized(false);
      setMarkdownContent(initialContent);
      setPlatforms([]);
      setSelectedCategoryIds([]);
      setSelectedConfig(null);
      setPathPatternDerived(false);
      contentManuallyEdited.current = false;
      previousTemplateRef.current = '';
    }
  }, [open, initialContent]);

  // V2: Sync selectedConfig when entity_type changes (including default on mount)
  const handleEntityTypeChange = useCallback(
    (typeSlug: string) => {
      setValue('entity_type', typeSlug as ContextEntityType);

      const config = entityTypeConfigs.find((c) => c.slug === typeSlug) ?? null;
      setSelectedConfig(config);

      // Inject content template when switching types
      if (CREATION_FORM_V2 && !isEditMode) {
        // Content is "safe to replace" if it's empty or still matches the previous type's template
        const currentContentMatchesPreviousTemplate =
          !markdownContent.trim() ||
          markdownContent.trim() === previousTemplateRef.current.trim();

        if (currentContentMatchesPreviousTemplate) {
          const newTemplate = config?.content_template || '';
          setMarkdownContent(newTemplate);
          previousTemplateRef.current = newTemplate;
          contentManuallyEdited.current = false;
        }
        // If content doesn't match previous template, user has edited it — preserve their changes
      }

      // If the new type restricts applicable platforms, clear any incompatible selections
      if (CREATION_FORM_V2 && config?.applicable_platforms !== null && config?.applicable_platforms !== undefined) {
        const allowed = config.applicable_platforms;
        setPlatforms((prev) => prev.filter((p) => allowed.includes(p)));
      }

      // Auto-derive path pattern
      if (CREATION_FORM_V2 && !isEditMode) {
        const derived = derivePathPattern(config, platforms);
        setValue('path_pattern', derived);
        setPathPatternDerived(true);
      }
    },
    [entityTypeConfigs, platforms, markdownContent, isEditMode, setValue]
  );

  // V2: When platforms change, re-derive path if currently auto-derived
  const handlePlatformsChange = useCallback(
    (newPlatforms: string[]) => {
      setPlatforms(newPlatforms);
      if (CREATION_FORM_V2 && pathPatternDerived && !isEditMode) {
        const derived = derivePathPattern(selectedConfig, newPlatforms);
        setValue('path_pattern', derived);
      }
    },
    [pathPatternDerived, selectedConfig, isEditMode, setValue]
  );

  // V2: Sync selectedConfig on mount / when entity loads
  useEffect(() => {
    if (CREATION_FORM_V2 && watchedEntityType && entityTypeConfigs.length > 0 && !selectedConfig) {
      const config = entityTypeConfigs.find((c) => c.slug === watchedEntityType) ?? null;
      setSelectedConfig(config);
    }
  }, [watchedEntityType, entityTypeConfigs, selectedConfig]);

  // V2: Populate selectedCategoryIds from entity in edit mode when dialog opens
  useEffect(() => {
    if (CREATION_FORM_V2 && open && isEditMode && entity?.category_ids) {
      setSelectedCategoryIds(entity.category_ids);
    }
  }, [open, isEditMode, entity?.category_ids]);

  const handleMarkdownChange = useCallback(
    (content: string) => {
      setMarkdownContent(content);
      // Mark as manually edited only if content diverges from the current template
      if (CREATION_FORM_V2 && !isEditMode) {
        contentManuallyEdited.current =
          content.trim() !== previousTemplateRef.current.trim();
      }
    },
    [isEditMode]
  );

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

      // Build request data (same structure for both create and update)
      const requestData = {
        name: data.name,
        entity_type: data.entity_type,
        content: markdownContent,
        path_pattern: data.path_pattern,
        description: data.description || undefined,
        auto_load: data.auto_load,
        version: data.version || undefined,
        ...(CREATION_FORM_V2 && platforms.length > 0
          ? { target_platforms: platforms as Platform[] }
          : {}),
        ...(CREATION_FORM_V2 ? { category_ids: selectedCategoryIds } : {}),
      };

      // Call appropriate mutation
      if (isEditMode && entity) {
        await updateEntity.mutateAsync({
          id: entity.id,
          data: requestData as UpdateContextEntityRequest,
        });
      } else {
        await createEntity.mutateAsync(requestData as CreateContextEntityRequest);
      }

      // Success - call parent callback
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    }
  };

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="flex h-[90vh] max-w-6xl flex-col">
        <DialogHeader>
          <DialogTitle>{isEditMode ? 'Edit Context Entity' : 'Create Context Entity'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col overflow-hidden">
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
              {CREATION_FORM_V2 ? (
                <V2FormFields
                  control={control}
                  register={register}
                  errors={errors}
                  isLoading={isLoading}
                  entityTypeConfigs={entityTypeConfigs}
                  selectedConfig={selectedConfig}
                  onEntityTypeChange={handleEntityTypeChange}
                  platforms={platforms}
                  onPlatformsChange={handlePlatformsChange}
                  pathPatternDerived={pathPatternDerived}
                  onPathPatternEdit={() => setPathPatternDerived(false)}
                  selectedCategoryIds={selectedCategoryIds}
                  onCategoryIdsChange={setSelectedCategoryIds}
                  availablePlatformOptions={getFilteredPlatformOptions(selectedConfig)}
                />
              ) : (
                <>
                  {/* V1 legacy fields */}
                  {/* Name field */}
                  <div className="space-y-2">
                    <Label htmlFor="name">
                      Name
                      <span className="ml-1 text-destructive" aria-hidden="true">*</span>
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
                      aria-required="true"
                      aria-invalid={!!errors.name}
                      aria-describedby={errors.name ? 'name-error' : undefined}
                    />
                    {errors.name && (
                      <p id="name-error" className="text-sm text-destructive" role="alert">
                        {errors.name.message}
                      </p>
                    )}
                  </div>

                  {/* Entity type field */}
                  <div className="space-y-2">
                    <Label htmlFor="entity_type">
                      Entity Type
                      <span className="ml-1 text-destructive" aria-hidden="true">*</span>
                    </Label>
                    <Controller
                      name="entity_type"
                      control={control}
                      rules={{ required: 'Entity type is required' }}
                      render={({ field: { onChange, value } }) => (
                        <Select value={value} onValueChange={onChange} disabled={isLoading}>
                          <SelectTrigger
                            id="entity_type"
                            aria-required="true"
                            aria-invalid={!!errors.entity_type}
                            aria-describedby={errors.entity_type ? 'entity-type-error' : undefined}
                            className="[&_[data-description]]:hidden"
                          >
                            <SelectValue placeholder="Select entity type..." />
                          </SelectTrigger>
                          <SelectContent>
                            {ENTITY_TYPE_OPTIONS.map((option) => (
                              <SelectItem key={option.value} value={option.value}>
                                <div>
                                  <div className="font-medium">{option.label}</div>
                                  <div data-description className="text-xs text-muted-foreground">
                                    {option.description}
                                  </div>
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                    {errors.entity_type && (
                      <p id="entity-type-error" className="text-sm text-destructive" role="alert">
                        {errors.entity_type.message}
                      </p>
                    )}
                  </div>

                  {/* Path pattern field */}
                  <div className="space-y-2">
                    <Label htmlFor="path_pattern">
                      Path Pattern
                      <span className="ml-1 text-destructive" aria-hidden="true">*</span>
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
                      aria-required="true"
                      aria-invalid={!!errors.path_pattern}
                      aria-describedby={errors.path_pattern ? 'path-pattern-error path_pattern-help' : 'path_pattern-help'}
                    />
                    <p id="path_pattern-help" className="text-xs text-muted-foreground">
                      Must start with{' '}
                      <code className="rounded bg-muted px-1 py-0.5">.claude/</code>
                    </p>
                    {errors.path_pattern && (
                      <p id="path-pattern-error" className="text-sm text-destructive" role="alert">
                        {errors.path_pattern.message}
                      </p>
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

                  {/* Category field (V1 legacy — plain text, not multi-select) */}
                  <div className="space-y-2">
                    <Label htmlFor="category">Category</Label>
                    <Input
                      id="category"
                      defaultValue={entity?.category || ''}
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
                    <p id="version-help" className="text-xs text-muted-foreground">
                      Semantic versioning recommended
                    </p>
                  </div>
                </>
              )}
            </div>

            {/* Right column: Markdown editor */}
            <div className="flex flex-1 flex-col space-y-2 overflow-hidden lg:w-2/3">
              {/* Use a <p> as a label since CodeMirror renders a contenteditable div, not a native input */}
              <p
                id="content-label"
                className="text-sm font-medium leading-none"
                aria-hidden="true"
              >
                Content
                <span className="ml-1 text-destructive" aria-hidden="true">*</span>
              </p>
              <div
                className="flex-1 overflow-hidden"
                role="group"
                aria-labelledby="content-label"
                aria-describedby="content-help"
                aria-required="true"
              >
                {isEditMode && isContentLoading ? (
                  <div
                    className="flex h-full items-center justify-center rounded-md border bg-muted/50"
                    role="status"
                    aria-live="polite"
                  >
                    <Loader2
                      className="h-6 w-6 animate-spin text-muted-foreground"
                      aria-hidden="true"
                    />
                    <span className="ml-2 text-sm text-muted-foreground">Loading content...</span>
                  </div>
                ) : (
                  <MarkdownEditor
                    initialContent={markdownContent}
                    onChange={handleMarkdownChange}
                    readOnly={isLoading}
                    className="h-full"
                  />
                )}
              </div>
              <p id="content-help" className="text-xs text-muted-foreground">
                Markdown content for this context entity
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="mt-6 flex justify-end gap-3 border-t pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
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
      </DialogContent>
    </Dialog>
  );
}
