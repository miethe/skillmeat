/**
 * MemoryFormModal Component (UI-3.6)
 *
 * A dialog for creating new memories or editing existing ones. Supports all
 * memory types from the SDK, confidence scoring with tier-colored indicators,
 * and optional TTL policy configuration.
 *
 * Uses shadcn Dialog with form controls (Select, Textarea, Input) and
 * mutation hooks from @/hooks for API submission.
 */

'use client';

import * as React from 'react';
import { useState, useEffect, useCallback } from 'react';
import { Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { useCreateMemoryItem, useUpdateMemoryItem } from '@/hooks';
import type { MemoryItemResponse } from '@/sdk/models/MemoryItemResponse';
import type { MemoryType } from '@/sdk/models/MemoryType';
import {
  getConfidenceTier,
  getConfidenceColorClasses,
} from './memory-utils';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** All memory types from the SDK MemoryType enum. */
const MEMORY_TYPES: { value: MemoryType; label: string }[] = [
  { value: 'constraint', label: 'Constraint' },
  { value: 'decision', label: 'Decision' },
  { value: 'gotcha', label: 'Gotcha' },
  { value: 'learning', label: 'Learning' },
  { value: 'style_rule', label: 'Style Rule' },
];

const MIN_CONTENT_LENGTH = 10;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface MemoryFormModalProps {
  /** Whether the dialog is open. */
  open: boolean;
  /** Callback to control open state. */
  onOpenChange: (open: boolean) => void;
  /** Existing memory to edit (null/undefined = create mode). */
  memory?: MemoryItemResponse | null;
  /** Project ID for creating new memory items. */
  projectId: string;
  /** Callback after successful create/update. */
  onSuccess?: () => void;
}

// ---------------------------------------------------------------------------
// Form State
// ---------------------------------------------------------------------------

interface FormState {
  type: MemoryType;
  content: string;
  confidence: number; // 0-100 integer for UI; converted to 0-1 for API
  revalidateDays: string;
  deprecateUnusedDays: string;
}

interface FormErrors {
  type?: string;
  content?: string;
  confidence?: string;
}

function getInitialState(memory?: MemoryItemResponse | null): FormState {
  if (memory) {
    const ttlPolicy = memory.ttl_policy as Record<string, number> | null | undefined;
    return {
      type: memory.type as MemoryType,
      content: memory.content,
      confidence: Math.round(memory.confidence * 100),
      revalidateDays: ttlPolicy?.revalidate_after_days?.toString() ?? '',
      deprecateUnusedDays: ttlPolicy?.deprecate_unused_after_days?.toString() ?? '',
    };
  }
  return {
    type: 'decision',
    content: '',
    confidence: 75,
    revalidateDays: '',
    deprecateUnusedDays: '',
  };
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * MemoryFormModal -- create or edit a memory item.
 *
 * In create mode (no memory prop), shows an empty form.
 * In edit mode (memory prop provided), pre-fills all fields.
 *
 * @example
 * ```tsx
 * // Create mode
 * <MemoryFormModal
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   projectId="proj-123"
 *   onSuccess={() => toast({ title: "Created!" })}
 * />
 *
 * // Edit mode
 * <MemoryFormModal
 *   open={isOpen}
 *   onOpenChange={setIsOpen}
 *   memory={selectedMemory}
 *   projectId="proj-123"
 * />
 * ```
 */
export function MemoryFormModal({
  open,
  onOpenChange,
  memory,
  projectId,
  onSuccess,
}: MemoryFormModalProps) {
  const isEditMode = !!memory;

  // ---------------------------------------------------------------------------
  // Form state
  // ---------------------------------------------------------------------------
  const [form, setForm] = useState<FormState>(() => getInitialState(memory));
  const [errors, setErrors] = useState<FormErrors>({});
  const [showTtl, setShowTtl] = useState(
    () => !!(memory?.ttl_policy && Object.keys(memory.ttl_policy).length > 0)
  );

  // Reset form when dialog opens or memory changes
  useEffect(() => {
    if (open) {
      setForm(getInitialState(memory));
      setErrors({});
      setShowTtl(!!(memory?.ttl_policy && Object.keys(memory.ttl_policy).length > 0));
    }
  }, [open, memory]);

  // ---------------------------------------------------------------------------
  // Mutations
  // ---------------------------------------------------------------------------
  const createMutation = useCreateMemoryItem({
    onSuccess: () => {
      onOpenChange(false);
      onSuccess?.();
    },
  });

  const updateMutation = useUpdateMemoryItem({
    onSuccess: () => {
      onOpenChange(false);
      onSuccess?.();
    },
  });

  const isSubmitting = createMutation.isPending || updateMutation.isPending;

  // ---------------------------------------------------------------------------
  // Validation
  // ---------------------------------------------------------------------------
  const validate = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!form.type) {
      newErrors.type = 'Type is required';
    }

    if (!form.content || form.content.trim().length < MIN_CONTENT_LENGTH) {
      newErrors.content = `Content must be at least ${MIN_CONTENT_LENGTH} characters`;
    }

    if (form.confidence < 0 || form.confidence > 100) {
      newErrors.confidence = 'Confidence must be between 0 and 100';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [form]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------
  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();

      if (!validate()) return;

      // Build TTL policy if values are set
      let ttlPolicy: Record<string, number> | null = null;
      const revalidateDays = parseInt(form.revalidateDays, 10);
      const deprecateDays = parseInt(form.deprecateUnusedDays, 10);

      if (!isNaN(revalidateDays) || !isNaN(deprecateDays)) {
        ttlPolicy = {};
        if (!isNaN(revalidateDays) && revalidateDays > 0) {
          ttlPolicy.revalidate_after_days = revalidateDays;
        }
        if (!isNaN(deprecateDays) && deprecateDays > 0) {
          ttlPolicy.deprecate_unused_after_days = deprecateDays;
        }
        // If both are empty/invalid, keep null
        if (Object.keys(ttlPolicy).length === 0) {
          ttlPolicy = null;
        }
      }

      if (isEditMode && memory) {
        updateMutation.mutate({
          itemId: memory.id,
          data: {
            type: form.type,
            content: form.content.trim(),
            confidence: form.confidence / 100,
            ttl_policy: ttlPolicy,
          },
        });
      } else {
        createMutation.mutate({
          projectId,
          data: {
            type: form.type,
            content: form.content.trim(),
            confidence: form.confidence / 100,
            ttl_policy: ttlPolicy,
          },
        });
      }
    },
    [form, isEditMode, memory, projectId, validate, createMutation, updateMutation]
  );

  const updateField = useCallback(
    <K extends keyof FormState>(key: K, value: FormState[K]) => {
      setForm((prev) => ({ ...prev, [key]: value }));
      // Clear error for this field on change
      setErrors((prev) => ({ ...prev, [key]: undefined }));
    },
    []
  );

  // ---------------------------------------------------------------------------
  // Confidence color indicator
  // ---------------------------------------------------------------------------
  const confidenceTier = getConfidenceTier(form.confidence / 100);
  const confidenceColors = getConfidenceColorClasses(confidenceTier);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {isEditMode ? 'Edit Memory' : 'Create Memory'}
          </DialogTitle>
          <DialogDescription>
            {isEditMode
              ? 'Update the memory item details below.'
              : 'Add a new memory item to this project.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Type selector */}
          <div className="space-y-2">
            <Label htmlFor="memory-type">
              Type <span className="text-destructive" aria-hidden="true">*</span>
            </Label>
            <Select
              value={form.type}
              onValueChange={(value) => updateField('type', value as MemoryType)}
              required
            >
              <SelectTrigger
                id="memory-type"
                aria-label="Memory type"
                aria-required="true"
                aria-describedby={errors.type ? 'type-error' : undefined}
              >
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                {MEMORY_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {errors.type && (
              <p id="type-error" className="text-xs text-destructive" role="alert">{errors.type}</p>
            )}
          </div>

          {/* Content textarea */}
          <div className="space-y-2">
            <Label htmlFor="memory-content">
              Content <span className="text-destructive" aria-hidden="true">*</span>
            </Label>
            <Textarea
              id="memory-content"
              placeholder="Describe the memory (decision, constraint, learning, etc.)..."
              value={form.content}
              onChange={(e) => updateField('content', e.target.value)}
              rows={4}
              className={cn(errors.content && 'border-destructive')}
              aria-required="true"
              aria-describedby={[
                errors.content ? 'content-error' : 'content-hint',
                'content-count',
              ].join(' ')}
              aria-invalid={!!errors.content}
            />
            <div className="flex items-center justify-between">
              {errors.content ? (
                <p id="content-error" className="text-xs text-destructive" role="alert">
                  {errors.content}
                </p>
              ) : (
                <p id="content-hint" className="text-xs text-muted-foreground">
                  Minimum {MIN_CONTENT_LENGTH} characters
                </p>
              )}
              <p id="content-count" className="text-xs text-muted-foreground" aria-live="polite">
                {form.content.length} chars
              </p>
            </div>
          </div>

          {/* Confidence input */}
          <div className="space-y-2">
            <Label htmlFor="memory-confidence">Confidence</Label>
            <div className="flex items-center gap-3">
              <input
                id="memory-confidence"
                type="range"
                min={0}
                max={100}
                value={form.confidence}
                onChange={(e) =>
                  updateField('confidence', parseInt(e.target.value, 10))
                }
                className="flex-1 accent-current"
                aria-label="Confidence percentage"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={form.confidence}
                aria-valuetext={`${form.confidence}%`}
                aria-describedby={errors.confidence ? 'confidence-error' : undefined}
              />
              <span
                className={cn(
                  'min-w-[3.5rem] rounded-md px-2 py-1 text-center text-sm font-medium',
                  confidenceColors.bg,
                  confidenceColors.text
                )}
              >
                {form.confidence}%
              </span>
            </div>
            {errors.confidence && (
              <p id="confidence-error" className="text-xs text-destructive" role="alert">{errors.confidence}</p>
            )}
          </div>

          {/* TTL Policy (collapsible) */}
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setShowTtl(!showTtl)}
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {showTtl ? '- Hide TTL Policy' : '+ TTL Policy (optional)'}
            </button>

            {showTtl && (
              <div className="space-y-3 rounded-md border p-3">
                <div className="space-y-1.5">
                  <Label htmlFor="memory-revalidate" className="text-xs">
                    Revalidate after (days)
                  </Label>
                  <Input
                    id="memory-revalidate"
                    type="number"
                    min={1}
                    placeholder="e.g. 30"
                    value={form.revalidateDays}
                    onChange={(e) => updateField('revalidateDays', e.target.value)}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="memory-deprecate-unused" className="text-xs">
                    Auto-deprecate if unused for (days)
                  </Label>
                  <Input
                    id="memory-deprecate-unused"
                    type="number"
                    min={1}
                    placeholder="e.g. 90"
                    value={form.deprecateUnusedDays}
                    onChange={(e) =>
                      updateField('deprecateUnusedDays', e.target.value)
                    }
                  />
                </div>
              </div>
            )}
          </div>

          {/* Mutation error display */}
          {(createMutation.error || updateMutation.error) && (
            <p className="text-sm text-destructive" role="alert">
              {createMutation.error?.message ||
                updateMutation.error?.message ||
                'An error occurred. Please try again.'}
            </p>
          )}

          {/* Footer */}
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} aria-busy={isSubmitting}>
              {isSubmitting && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              {isEditMode ? 'Save Changes' : 'Create Memory'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
