/**
 * ModuleEditor Component (UI-4.5)
 *
 * A card-based form/editor for creating and editing context modules. Handles
 * module metadata (name, description, priority), selector configuration
 * (memory types, min confidence, file patterns, workflow stages), and a
 * manual memory list with remove capability.
 *
 * In create mode (no `module` prop), renders an empty form.
 * In edit mode (`module` prop provided), pre-fills all fields.
 *
 * Uses shadcn/ui primitives (Input, Textarea, Checkbox, Badge, Button, Card,
 * Label, Separator) and mutation hooks from `@/hooks/use-context-modules`.
 */

'use client';

import * as React from 'react';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { Loader2, X, Plus, Eye, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import {
  useCreateContextModule,
  useUpdateContextModule,
  useModuleMemories,
  useRemoveMemoryFromModule,
  useAddMemoryToModule,
} from '@/hooks/use-context-modules';
import { useMemoryItems } from '@/hooks/use-memory-items';
import type { ContextModuleResponse } from '@/sdk/models/ContextModuleResponse';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import { MemoryTypeBadge } from './memory-type-badge';
import {
  getConfidenceTier,
  getConfidenceColorClasses,
} from './memory-utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** The five canonical memory types used by the selector builder. */
const SELECTOR_MEMORY_TYPES: { value: string; label: string }[] = [
  { value: 'decision', label: 'Decision' },
  { value: 'constraint', label: 'Constraint' },
  { value: 'gotcha', label: 'Gotcha' },
  { value: 'style_rule', label: 'Style Rule' },
  { value: 'learning', label: 'Learning' },
];

const MIN_NAME_LENGTH = 1;
const MAX_NAME_LENGTH = 255;
const MIN_PRIORITY = 0;
const MAX_PRIORITY = 100;
const DEFAULT_PRIORITY = 5;
const MIN_CONFIDENCE_SELECTOR = 0;
const MAX_CONFIDENCE_SELECTOR = 1;
const CONFIDENCE_STEP = 0.05;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ModuleEditorProps {
  /** Existing module to edit (undefined = create mode). */
  module?: ContextModuleResponse;
  /** Project ID for creating/updating modules. */
  projectId: string;
  /** Callback after successful create/update. */
  onSave?: (module: ContextModuleResponse) => void;
  /** Callback when the user cancels editing. */
  onCancel?: () => void;
  /** Callback to preview the pack for this module. */
  onPreview?: (moduleId: string) => void;
}

// ---------------------------------------------------------------------------
// Form State
// ---------------------------------------------------------------------------

interface Selectors {
  memory_types: string[];
  min_confidence: number;
  file_patterns: string[];
  workflow_stages: string[];
}

interface FormState {
  name: string;
  description: string;
  priority: number;
  selectors: Selectors;
}

interface FormErrors {
  name?: string;
  priority?: string;
}

function parseSelectors(raw?: Record<string, any> | null): Selectors {
  return {
    memory_types: Array.isArray(raw?.memory_types) ? raw.memory_types : [],
    min_confidence:
      typeof raw?.min_confidence === 'number' ? raw.min_confidence : 0,
    file_patterns: Array.isArray(raw?.file_patterns) ? raw.file_patterns : [],
    workflow_stages: Array.isArray(raw?.workflow_stages)
      ? raw.workflow_stages
      : [],
  };
}

function getInitialState(module?: ContextModuleResponse): FormState {
  if (module) {
    return {
      name: module.name,
      description: module.description ?? '',
      priority: module.priority ?? DEFAULT_PRIORITY,
      selectors: parseSelectors(module.selectors),
    };
  }
  return {
    name: '',
    description: '',
    priority: DEFAULT_PRIORITY,
    selectors: {
      memory_types: [],
      min_confidence: 0,
      file_patterns: [],
      workflow_stages: [],
    },
  };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * TagInput -- a small input that manages a list of string tags.
 * Tags are added by pressing Enter or comma, and removed by clicking the X.
 */
function TagInput({
  id,
  label,
  placeholder,
  values,
  onChange,
  tooltip,
}: {
  id: string;
  label: string;
  placeholder: string;
  values: string[];
  onChange: (values: string[]) => void;
  tooltip?: string;
}) {
  const [inputValue, setInputValue] = useState('');

  const addTag = useCallback(
    (raw: string) => {
      const tag = raw.trim();
      if (tag && !values.includes(tag)) {
        onChange([...values, tag]);
      }
      setInputValue('');
    },
    [values, onChange]
  );

  const removeTag = useCallback(
    (index: number) => {
      onChange(values.filter((_, i) => i !== index));
    },
    [values, onChange]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag(inputValue);
      }
      if (e.key === 'Backspace' && inputValue === '' && values.length > 0) {
        removeTag(values.length - 1);
      }
    },
    [inputValue, values, addTag, removeTag]
  );

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5">
        <Label htmlFor={id} className="text-sm">
          {label}
        </Label>
        {tooltip && (
          <TooltipProvider delayDuration={300}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="inline-flex text-muted-foreground hover:text-foreground"
                  aria-label={`Info about ${label}`}
                >
                  <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" align="start" collisionPadding={16} className="max-w-xs text-xs">
                <p>{tooltip}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      {values.length > 0 && (
        <div className="flex flex-wrap gap-1.5" role="list" aria-label={label}>
          {values.map((tag, index) => (
            <span
              key={`${tag}-${index}`}
              role="listitem"
              className="inline-flex items-center gap-1 rounded-md border bg-muted/50 px-2 py-0.5 text-xs"
            >
              {tag}
              <button
                type="button"
                onClick={() => removeTag(index)}
                className="rounded-sm text-muted-foreground hover:text-foreground"
                aria-label={`Remove ${tag}`}
              >
                <X className="h-3 w-3" aria-hidden="true" />
              </button>
            </span>
          ))}
        </div>
      )}
      <Input
        id={id}
        type="text"
        placeholder={placeholder}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={() => {
          if (inputValue.trim()) addTag(inputValue);
        }}
        className="h-8 text-sm"
        aria-describedby={`${id}-hint`}
      />
      <p id={`${id}-hint`} className="text-[11px] text-muted-foreground">
        Press Enter or comma to add
      </p>
    </div>
  );
}

/**
 * ManualMemoryRow -- a single row in the manual memory list with badge,
 * content preview, confidence, and remove button.
 */
function ManualMemoryRow({
  memory,
  onRemove,
  isRemoving,
}: {
  memory: MemoryItemResponse;
  onRemove: () => void;
  isRemoving: boolean;
}) {
  const tier = getConfidenceTier(memory.confidence);
  const colors = getConfidenceColorClasses(tier);
  const truncatedContent =
    memory.content.length > 80
      ? memory.content.slice(0, 80) + '...'
      : memory.content;

  return (
    <div className="flex items-center gap-3 rounded-md border p-2">
      <MemoryTypeBadge type={memory.type} />
      <span className="flex-1 truncate text-sm text-muted-foreground">
        {truncatedContent}
      </span>
      <span
        className={cn(
          'rounded-md px-1.5 py-0.5 text-xs font-medium',
          colors.bg,
          colors.text
        )}
      >
        {Math.round(memory.confidence * 100)}%
      </span>
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="h-7 w-7 p-0"
        onClick={onRemove}
        disabled={isRemoving}
        aria-label={`Remove memory: ${truncatedContent}`}
      >
        {isRemoving ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        ) : (
          <X className="h-3.5 w-3.5" aria-hidden="true" />
        )}
      </Button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * ModuleEditor -- create or edit a context module.
 *
 * In create mode (no module prop), shows an empty form.
 * In edit mode (module prop provided), pre-fills all fields and shows the
 * manual memory list.
 *
 * @example
 * ```tsx
 * // Create mode
 * <ModuleEditor
 *   projectId="proj-123"
 *   onSave={(mod) => console.log('Created', mod)}
 *   onCancel={() => router.back()}
 * />
 *
 * // Edit mode
 * <ModuleEditor
 *   module={existingModule}
 *   projectId="proj-123"
 *   onSave={(mod) => toast({ title: 'Updated!' })}
 *   onCancel={() => router.back()}
 *   onPreview={(id) => openPackPreview(id)}
 * />
 * ```
 */
export function ModuleEditor({
  module,
  projectId,
  onSave,
  onCancel,
  onPreview,
}: ModuleEditorProps) {
  const isEditMode = !!module;

  // -------------------------------------------------------------------------
  // Form state
  // -------------------------------------------------------------------------
  const [form, setForm] = useState<FormState>(() => getInitialState(module));
  const [errors, setErrors] = useState<FormErrors>({});
  const [addMemoryOpen, setAddMemoryOpen] = useState(false);
  const [memorySearch, setMemorySearch] = useState('');

  // Reset form when module changes (e.g. navigating between modules)
  useEffect(() => {
    setForm(getInitialState(module));
    setErrors({});
  }, [module]);

  // -------------------------------------------------------------------------
  // Mutations
  // -------------------------------------------------------------------------
  const createMutation = useCreateContextModule({
    onSuccess: (data: ContextModuleResponse) => {
      onSave?.(data);
    },
  });

  const updateMutation = useUpdateContextModule({
    onSuccess: (data: ContextModuleResponse) => {
      onSave?.(data);
    },
  });

  const removeMutation = useRemoveMemoryFromModule();
  const addMutation = useAddMemoryToModule();

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  // -------------------------------------------------------------------------
  // Manual memory list (edit mode only)
  // -------------------------------------------------------------------------
  const memoriesQuery = useModuleMemories(
    isEditMode ? module!.id : ''
  );

  const manualMemories: MemoryItemResponse[] = useMemo(
    () => (memoriesQuery.data as MemoryItemResponse[] | undefined) ?? [],
    [memoriesQuery.data]
  );
  const manualMemoryIds = useMemo(
    () => new Set(manualMemories.map((m) => m.id)),
    [manualMemories]
  );

  const availableMemoriesQuery = useMemoryItems({
    projectId,
    search: memorySearch || undefined,
    limit: 50,
  });

  const availableMemories = useMemo(
    () =>
      (availableMemoriesQuery.data?.items ?? []).filter(
        (item) => item.status !== 'deprecated' && !manualMemoryIds.has(item.id)
      ),
    [availableMemoriesQuery.data?.items, manualMemoryIds]
  );

  // -------------------------------------------------------------------------
  // Validation
  // -------------------------------------------------------------------------
  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (
      !form.name.trim() ||
      form.name.trim().length < MIN_NAME_LENGTH ||
      form.name.trim().length > MAX_NAME_LENGTH
    ) {
      newErrors.name = `Name must be between ${MIN_NAME_LENGTH} and ${MAX_NAME_LENGTH} characters`;
    }

    if (
      form.priority < MIN_PRIORITY ||
      form.priority > MAX_PRIORITY ||
      !Number.isInteger(form.priority)
    ) {
      newErrors.priority = `Priority must be an integer between ${MIN_PRIORITY} and ${MAX_PRIORITY}`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [form.name, form.priority]);

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------
  const buildSelectorsPayload = useCallback((): Record<string, any> | null => {
    const s = form.selectors;
    const payload: Record<string, any> = {};

    if (s.memory_types.length > 0) payload.memory_types = s.memory_types;
    if (s.min_confidence > 0) payload.min_confidence = s.min_confidence;
    if (s.file_patterns.length > 0) payload.file_patterns = s.file_patterns;
    if (s.workflow_stages.length > 0)
      payload.workflow_stages = s.workflow_stages;

    return Object.keys(payload).length > 0 ? payload : null;
  }, [form.selectors]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (!validate()) return;

      const selectors = buildSelectorsPayload();

      if (isEditMode && module) {
        updateMutation.mutate({
          moduleId: module.id,
          data: {
            name: form.name.trim(),
            description: form.description.trim() || null,
            selectors,
            priority: form.priority,
          },
        });
      } else {
        createMutation.mutate({
          projectId,
          data: {
            name: form.name.trim(),
            description: form.description.trim() || null,
            selectors,
            priority: form.priority,
          },
        });
      }
    },
    [
      form,
      isEditMode,
      module,
      projectId,
      validate,
      buildSelectorsPayload,
      createMutation,
      updateMutation,
    ]
  );

  const updateField = useCallback(
    <K extends keyof FormState>(key: K, value: FormState[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    },
    []
  );

  const updateSelector = useCallback(
    <K extends keyof Selectors>(key: K, value: Selectors[K]) => {
      setForm((prev) => ({
        ...prev,
        selectors: { ...prev.selectors, [key]: value },
      }));
    },
    []
  );

  const toggleMemoryType = useCallback(
    (type: string) => {
      setForm((prev) => {
        const current = prev.selectors.memory_types;
        const next = current.includes(type)
          ? current.filter((t) => t !== type)
          : [...current, type];
        return {
          ...prev,
          selectors: { ...prev.selectors, memory_types: next },
        };
      });
    },
    []
  );

  const handleRemoveMemory = useCallback(
    (memoryId: string) => {
      if (!module) return;
      removeMutation.mutate({ moduleId: module.id, memoryId });
    },
    [module, removeMutation]
  );

  const handleAddMemory = useCallback(
    (memoryId: string) => {
      if (!module) return;
      addMutation.mutate(
        {
          moduleId: module.id,
          data: {
            memory_id: memoryId,
            ordering: manualMemories.length,
          },
        },
        {
          onSuccess: () => {
            setAddMemoryOpen(false);
            setMemorySearch('');
          },
        }
      );
    },
    [module, addMutation, manualMemories.length]
  );

  // -------------------------------------------------------------------------
  // Confidence display
  // -------------------------------------------------------------------------
  const confidencePercent = Math.round(form.selectors.min_confidence * 100);

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">
          {isEditMode ? 'Edit Context Module' : 'Create Context Module'}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* -------------------------------------------------------------- */}
          {/* Section 1: Module Metadata                                      */}
          {/* -------------------------------------------------------------- */}
          <div className="space-y-4">
            {/* Name */}
            <div className="space-y-2">
              <Label htmlFor="module-name">
                Name{' '}
                <span className="text-destructive" aria-hidden="true">
                  *
                </span>
              </Label>
              <Input
                id="module-name"
                placeholder="e.g. Frontend Decisions"
                value={form.name}
                onChange={(e) => updateField('name', e.target.value)}
                maxLength={MAX_NAME_LENGTH}
                className={cn(errors.name && 'border-destructive')}
                aria-required="true"
                aria-describedby={errors.name ? 'name-error' : 'name-hint'}
                aria-invalid={!!errors.name}
              />
              {errors.name ? (
                <p
                  id="name-error"
                  className="text-xs text-destructive"
                  role="alert"
                >
                  {errors.name}
                </p>
              ) : (
                <p id="name-hint" className="text-xs text-muted-foreground">
                  1-255 characters
                </p>
              )}
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="module-description">Description</Label>
              <Textarea
                id="module-description"
                placeholder="Describe the purpose of this context module..."
                value={form.description}
                onChange={(e) => updateField('description', e.target.value)}
                rows={3}
              />
            </div>

            {/* Priority */}
            <div className="space-y-2">
              <Label htmlFor="module-priority">Priority</Label>
              <div className="flex items-center gap-3">
                <Input
                  id="module-priority"
                  type="number"
                  min={MIN_PRIORITY}
                  max={MAX_PRIORITY}
                  value={form.priority}
                  onChange={(e) => {
                    const val = parseInt(e.target.value, 10);
                    if (!isNaN(val)) {
                      updateField(
                        'priority',
                        Math.max(MIN_PRIORITY, Math.min(MAX_PRIORITY, val))
                      );
                    }
                  }}
                  className={cn('w-24', errors.priority && 'border-destructive')}
                  aria-describedby={
                    errors.priority ? 'priority-error' : 'priority-hint'
                  }
                  aria-invalid={!!errors.priority}
                />
                <span className="text-xs text-muted-foreground">
                  0 (lowest) to 100 (highest)
                </span>
              </div>
              {errors.priority && (
                <p
                  id="priority-error"
                  className="text-xs text-destructive"
                  role="alert"
                >
                  {errors.priority}
                </p>
              )}
              {!errors.priority && (
                <p
                  id="priority-hint"
                  className="sr-only"
                >
                  Module priority for ordering, 0 to 100
                </p>
              )}
            </div>
          </div>

          <Separator />

          {/* -------------------------------------------------------------- */}
          {/* Section 2: Selector Builder                                     */}
          {/* -------------------------------------------------------------- */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Selectors</h3>

            {/* Memory Types (checkbox group) */}
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">Memory Types</legend>
              <div
                className="flex flex-wrap gap-x-4 gap-y-2"
                role="group"
                aria-label="Memory type selectors"
              >
                {SELECTOR_MEMORY_TYPES.map((mt) => (
                  <label
                    key={mt.value}
                    className="flex items-center gap-2 text-sm"
                  >
                    <Checkbox
                      checked={form.selectors.memory_types.includes(mt.value)}
                      onCheckedChange={() => toggleMemoryType(mt.value)}
                      aria-label={mt.label}
                    />
                    {mt.label}
                  </label>
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground">
                Leave all unchecked to include all types
              </p>
            </fieldset>

            {/* Min Confidence */}
            <div className="space-y-2">
              <Label htmlFor="selector-confidence" className="text-sm">
                Minimum Confidence
              </Label>
              <div className="flex items-center gap-3">
                <input
                  id="selector-confidence"
                  type="range"
                  min={MIN_CONFIDENCE_SELECTOR}
                  max={MAX_CONFIDENCE_SELECTOR}
                  step={CONFIDENCE_STEP}
                  value={form.selectors.min_confidence}
                  onChange={(e) =>
                    updateSelector(
                      'min_confidence',
                      parseFloat(e.target.value)
                    )
                  }
                  className="flex-1 accent-current"
                  aria-label="Minimum confidence threshold"
                  aria-valuemin={MIN_CONFIDENCE_SELECTOR}
                  aria-valuemax={MAX_CONFIDENCE_SELECTOR}
                  aria-valuenow={form.selectors.min_confidence}
                  aria-valuetext={`${confidencePercent}%`}
                />
                <span className="min-w-[3rem] rounded-md bg-muted px-2 py-1 text-center text-sm font-medium">
                  {confidencePercent}%
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Only include memories at or above this confidence level (0% = no
                filter)
              </p>
            </div>

            {/* File Patterns */}
            <TagInput
              id="selector-file-patterns"
              label="File Patterns"
              placeholder="e.g. src/components/**"
              values={form.selectors.file_patterns}
              onChange={(vals) => updateSelector('file_patterns', vals)}
              tooltip="Glob patterns to match source files. Memories associated with matching files will be included in this module. Example: src/components/**, **/*.test.ts"
            />

            {/* Workflow Stages */}
            <TagInput
              id="selector-workflow-stages"
              label="Workflow Stages"
              placeholder="e.g. planning, review"
              values={form.selectors.workflow_stages}
              onChange={(vals) => updateSelector('workflow_stages', vals)}
              tooltip="Development workflow stages to filter memories by. Only memories tagged with these stages will be included. Common stages: planning, implementation, review, debugging, deployment"
            />
          </div>

          {/* -------------------------------------------------------------- */}
          {/* Section 3: Manual Memory List (edit mode only)                  */}
          {/* -------------------------------------------------------------- */}
          {isEditMode && (
            <>
              <Separator />
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold">
                    Manual Memories
                    {manualMemories.length > 0 && (
                      <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                        ({manualMemories.length})
                      </span>
                    )}
                  </h3>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-7 text-xs"
                    onClick={() => setAddMemoryOpen(true)}
                    aria-label="Add memory to module"
                  >
                    <Plus className="mr-1 h-3 w-3" aria-hidden="true" />
                    Add Memory
                  </Button>
                </div>

                {memoriesQuery.isLoading && (
                  <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
                    <Loader2
                      className="h-4 w-4 animate-spin"
                      aria-hidden="true"
                    />
                    Loading memories...
                  </div>
                )}

                {!memoriesQuery.isLoading && manualMemories.length === 0 && (
                  <p className="py-3 text-center text-sm text-muted-foreground">
                    No memories manually added to this module.
                  </p>
                )}

                {manualMemories.length > 0 && (
                  <div className="space-y-2" role="list" aria-label="Manual memories">
                    {manualMemories.map((mem) => (
                      <div key={mem.id} role="listitem">
                        <ManualMemoryRow
                          memory={mem}
                          onRemove={() => handleRemoveMemory(mem.id)}
                          isRemoving={
                            removeMutation.isPending &&
                            removeMutation.variables?.memoryId === mem.id
                          }
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Mutation error display                                          */}
          {/* -------------------------------------------------------------- */}
          {(createMutation.error || updateMutation.error) && (
            <p className="text-sm text-destructive" role="alert">
              {createMutation.error?.message ||
                updateMutation.error?.message ||
                'An error occurred. Please try again.'}
            </p>
          )}

          {/* -------------------------------------------------------------- */}
          {/* Actions                                                         */}
          {/* -------------------------------------------------------------- */}
          <div className="flex items-center justify-end gap-2 pt-2">
            {isEditMode && onPreview && module && (
              <Button
                type="button"
                variant="outline"
                onClick={() => onPreview(module.id)}
                disabled={isSubmitting}
              >
                <Eye className="mr-2 h-4 w-4" aria-hidden="true" />
                Preview Pack
              </Button>
            )}
            <div className="flex-1" />
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting}
              aria-busy={isSubmitting}
            >
              {isSubmitting && (
                <Loader2
                  className="mr-2 h-4 w-4 animate-spin"
                  aria-hidden="true"
                />
              )}
              {isEditMode ? 'Save Changes' : 'Create Module'}
            </Button>
          </div>
        </form>
      </CardContent>
      {isEditMode && (
        <Dialog open={addMemoryOpen} onOpenChange={setAddMemoryOpen}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Add Memory to Module</DialogTitle>
              <DialogDescription>
                Search and select a memory item to include manually.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3">
              <Input
                placeholder="Search memories..."
                value={memorySearch}
                onChange={(e) => setMemorySearch(e.target.value)}
                aria-label="Search memories to add"
              />
              <div className="max-h-[360px] space-y-2 overflow-y-auto rounded-md border p-2">
                {availableMemoriesQuery.isLoading && (
                  <div className="flex items-center gap-2 px-2 py-3 text-sm text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    Loading memories...
                  </div>
                )}
                {!availableMemoriesQuery.isLoading && availableMemories.length === 0 && (
                  <p className="px-2 py-3 text-sm text-muted-foreground">
                    No matching memories available.
                  </p>
                )}
                {availableMemories.map((memory) => (
                  <div key={memory.id} className="flex items-start gap-2 rounded border p-2">
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <MemoryTypeBadge type={memory.type} />
                        {'confidence' in memory && typeof memory.confidence === 'number' && (
                          <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                            {Math.round(memory.confidence * 100)}%
                          </span>
                        )}
                        {'status' in memory && memory.status && (
                          <span className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground">
                            {memory.status}
                          </span>
                        )}
                      </div>
                      <p className="line-clamp-2 text-sm text-muted-foreground" title={memory.content}>
                        {memory.content}
                      </p>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="shrink-0"
                      onClick={() => handleAddMemory(memory.id)}
                      disabled={addMutation.isPending}
                    >
                      Add
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </Card>
  );
}
