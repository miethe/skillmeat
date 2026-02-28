/**
 * RunWorkflowDialog
 *
 * Modal dialog for configuring and launching a workflow execution. Renders
 * dynamic parameter fields based on the workflow's parameter schema, with an
 * optional collapsible advanced section for context module overrides.
 *
 * Features:
 * - Dynamic parameter form driven by WorkflowParameter type metadata
 * - Required-field validation with inline error messages
 * - Default-value pre-fill for all parameter types
 * - Loading state on the Run button during submission
 * - Error toast on failure; success callback with execution ID
 * - Collapsible advanced section for context module overrides
 * - Full keyboard accessibility (Escape, Tab, Enter on submit)
 *
 * @example
 * ```tsx
 * <RunWorkflowDialog
 *   workflow={selectedWorkflow}
 *   open={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   onSuccess={(executionId) => router.push(`/workflows/executions/${executionId}`)}
 * />
 * ```
 */

'use client';

import * as React from 'react';
import { Play, ChevronDown, ChevronRight, TriangleAlert } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { cn } from '@/lib/utils';
import { useRunWorkflow } from '@/hooks';
import type { Workflow, WorkflowParameter } from '@/types/workflow';
import { useToast } from '@/hooks';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface RunWorkflowDialogProps {
  /** Workflow to run. Dialog renders nothing meaningful when null. */
  workflow: Workflow | null;
  /** Controlled open state. */
  open: boolean;
  /** Called when the dialog should close (Cancel button, Escape, backdrop). */
  onClose: () => void;
  /**
   * Called after a successful execution start.
   * Receives the new execution ID so the caller can navigate to the dashboard.
   */
  onSuccess?: (executionId: string) => void;
}

/** Flat map from parameter name to its current form value. */
type ParameterValues = Record<string, string | number | boolean>;

/** Per-field validation error messages. */
type FieldErrors = Record<string, string>;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Derive the initial value for a single parameter from its defaultValue. */
function deriveDefaultValue(param: WorkflowParameter): string | number | boolean {
  if (param.defaultValue !== undefined && param.defaultValue !== null) {
    const ptype = param.type?.toLowerCase() ?? 'string';
    if (ptype === 'boolean') return Boolean(param.defaultValue);
    if (ptype === 'number' || ptype === 'integer') return Number(param.defaultValue);
    return String(param.defaultValue);
  }
  const ptype = param.type?.toLowerCase() ?? 'string';
  if (ptype === 'boolean') return false;
  if (ptype === 'number' || ptype === 'integer') return '';
  return '';
}

/** Build initial ParameterValues map from all workflow parameters. */
function buildInitialValues(params: Record<string, WorkflowParameter>): ParameterValues {
  const values: ParameterValues = {};
  for (const [name, param] of Object.entries(params)) {
    values[name] = deriveDefaultValue(param);
  }
  return values;
}

/** Validate all required parameters; return error map (empty if valid). */
function validateParameters(
  params: Record<string, WorkflowParameter>,
  values: ParameterValues
): FieldErrors {
  const errors: FieldErrors = {};
  for (const [name, param] of Object.entries(params)) {
    if (!param.required) continue;
    const value = values[name];
    const ptype = param.type?.toLowerCase() ?? 'string';
    if (ptype === 'boolean') continue; // boolean always has a value
    if (value === '' || value === undefined || value === null) {
      errors[name] = `${name} is required`;
    }
  }
  return errors;
}

/**
 * Convert raw form values to the typed Record<string, unknown> the API expects.
 * Coerces number/integer string inputs to JS numbers.
 */
function coerceValues(
  params: Record<string, WorkflowParameter>,
  values: ParameterValues
): Record<string, unknown> {
  const coerced: Record<string, unknown> = {};
  for (const [name, param] of Object.entries(params)) {
    const value = values[name];
    const ptype = param.type?.toLowerCase() ?? 'string';
    if (ptype === 'number' || ptype === 'integer') {
      coerced[name] = value === '' ? undefined : Number(value);
    } else if (ptype === 'boolean') {
      coerced[name] = Boolean(value);
    } else {
      coerced[name] = value === '' ? undefined : value;
    }
  }
  return coerced;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/** Single parameter form field, rendered according to the parameter type. */
function ParameterField({
  name,
  param,
  value,
  error,
  onChange,
}: {
  name: string;
  param: WorkflowParameter;
  value: string | number | boolean;
  error?: string;
  onChange: (name: string, value: string | number | boolean) => void;
}) {
  const ptype = param.type?.toLowerCase() ?? 'string';
  const inputId = `param-${name}`;
  const descId = param.description ? `param-desc-${name}` : undefined;
  const errorId = error ? `param-error-${name}` : undefined;

  const labelNode = (
    <Label
      htmlFor={ptype === 'boolean' ? undefined : inputId}
      className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
    >
      {name}
      {param.required && (
        <span className="ml-1 text-destructive" aria-hidden="true">
          *
        </span>
      )}
      {param.required && <span className="sr-only">(required)</span>}
    </Label>
  );

  const descNode = param.description ? (
    <p id={descId} className="text-xs text-muted-foreground">
      {param.description}
    </p>
  ) : null;

  const errorNode = error ? (
    <p id={errorId} role="alert" className="flex items-center gap-1 text-xs text-destructive">
      <TriangleAlert className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
      {error}
    </p>
  ) : null;

  // Boolean → Switch
  if (ptype === 'boolean') {
    return (
      <div className="flex items-center justify-between gap-4 rounded-lg border px-3 py-2.5">
        <div className="space-y-0.5">
          {labelNode}
          {descNode}
          {errorNode}
        </div>
        <Switch
          id={inputId}
          checked={Boolean(value)}
          onCheckedChange={(checked) => onChange(name, checked)}
          aria-describedby={[descId, errorId].filter(Boolean).join(' ') || undefined}
        />
      </div>
    );
  }

  // Multi-line text → Textarea
  if (ptype === 'text') {
    return (
      <div className="space-y-1.5">
        {labelNode}
        {descNode}
        <Textarea
          id={inputId}
          value={String(value)}
          onChange={(e) => onChange(name, e.target.value)}
          placeholder={`Enter ${name}…`}
          rows={3}
          aria-required={param.required}
          aria-invalid={Boolean(error)}
          aria-describedby={[descId, errorId].filter(Boolean).join(' ') || undefined}
          className={cn(error && 'border-destructive focus-visible:ring-destructive')}
        />
        {errorNode}
      </div>
    );
  }

  // Number / Integer → Input[type=number]
  if (ptype === 'number' || ptype === 'integer') {
    return (
      <div className="space-y-1.5">
        {labelNode}
        {descNode}
        <Input
          id={inputId}
          type="number"
          step={ptype === 'integer' ? 1 : undefined}
          value={String(value)}
          onChange={(e) => onChange(name, e.target.value)}
          placeholder={`Enter ${name}…`}
          aria-required={param.required}
          aria-invalid={Boolean(error)}
          aria-describedby={[descId, errorId].filter(Boolean).join(' ') || undefined}
          className={cn(error && 'border-destructive focus-visible:ring-destructive')}
        />
        {errorNode}
      </div>
    );
  }

  // String (default) → Input[type=text]
  return (
    <div className="space-y-1.5">
      {labelNode}
      {descNode}
      <Input
        id={inputId}
        type="text"
        value={String(value)}
        onChange={(e) => onChange(name, e.target.value)}
        placeholder={`Enter ${name}…`}
        aria-required={param.required}
        aria-invalid={Boolean(error)}
        aria-describedby={[descId, errorId].filter(Boolean).join(' ') || undefined}
        className={cn(error && 'border-destructive focus-visible:ring-destructive')}
      />
      {errorNode}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * RunWorkflowDialog
 *
 * Dialog for configuring and launching a workflow execution. Dynamic parameter
 * fields are rendered according to the workflow's parameter schema. An
 * optional collapsible advanced section exposes context module override input.
 */
export function RunWorkflowDialog({
  workflow,
  open,
  onClose,
  onSuccess,
}: RunWorkflowDialogProps) {
  const { toast } = useToast();
  const runWorkflow = useRunWorkflow();

  // -------------------------------------------------------------------------
  // Parameter form state
  // -------------------------------------------------------------------------

  const [paramValues, setParamValues] = React.useState<ParameterValues>({});
  const [fieldErrors, setFieldErrors] = React.useState<FieldErrors>({});
  const [submitError, setSubmitError] = React.useState<string | null>(null);

  // Advanced (context overrides) section
  const [advancedOpen, setAdvancedOpen] = React.useState(false);
  const [contextOverrides, setContextOverrides] = React.useState('');

  // Reset form whenever the dialog opens with a (potentially new) workflow.
  React.useEffect(() => {
    if (open && workflow) {
      setParamValues(buildInitialValues(workflow.parameters ?? {}));
      setFieldErrors({});
      setSubmitError(null);
      setAdvancedOpen(false);
      setContextOverrides('');
    }
  }, [open, workflow]);

  // -------------------------------------------------------------------------
  // Handlers
  // -------------------------------------------------------------------------

  function handleParamChange(name: string, value: string | number | boolean) {
    setParamValues((prev) => ({ ...prev, [name]: value }));
    // Clear error for the field on change.
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
  }

  async function handleRun() {
    if (!workflow) return;

    setSubmitError(null);

    // Validate required parameters.
    const errors = validateParameters(workflow.parameters ?? {}, paramValues);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    const coerced = coerceValues(workflow.parameters ?? {}, paramValues);

    // Build optional overrides map from the context textarea.
    let overrides: Record<string, unknown> | undefined;
    if (contextOverrides.trim()) {
      overrides = { contextModules: contextOverrides.trim() };
    }

    runWorkflow.mutate(
      { workflowId: workflow.id, parameters: coerced, overrides },
      {
        onSuccess: (execution) => {
          toast({
            title: 'Workflow started',
            description: `"${workflow.name}" is now running.`,
          });
          onClose();
          onSuccess?.(execution.id);
        },
        onError: (err) => {
          const message = err instanceof Error ? err.message : 'An unexpected error occurred.';
          setSubmitError(message);
          toast({
            title: 'Failed to start workflow',
            description: message,
            variant: 'destructive',
          });
        },
      }
    );
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleRun();
    }
  }

  // -------------------------------------------------------------------------
  // Derived values
  // -------------------------------------------------------------------------

  const hasParameters =
    workflow != null && Object.keys(workflow.parameters ?? {}).length > 0;

  const isRunning = runWorkflow.isPending;

  const descriptionText = workflow?.description
    ? workflow.description.length > 200
      ? `${workflow.description.slice(0, 197)}…`
      : workflow.description
    : undefined;

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent
        className="sm:max-w-[520px]"
        aria-label={workflow ? `Run workflow: ${workflow.name}` : 'Run workflow'}
        onKeyDown={handleKeyDown}
      >
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-lg font-semibold">
            <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-md bg-indigo-50 text-indigo-500 dark:bg-indigo-500/15 dark:text-indigo-400">
              <Play className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
            </span>
            Run {workflow?.name ?? 'Workflow'}
          </DialogTitle>

          {descriptionText && (
            <DialogDescription className="text-sm text-muted-foreground leading-relaxed">
              {descriptionText}
            </DialogDescription>
          )}
        </DialogHeader>

        {/* Body */}
        <div className="mt-2 space-y-5 max-h-[60vh] overflow-y-auto pr-1">
          {/* Parameters section */}
          {hasParameters && (
            <section aria-label="Workflow parameters">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Parameters
              </h3>
              <div className="space-y-4">
                {Object.entries(workflow!.parameters).map(([name, param]) => (
                  <ParameterField
                    key={name}
                    name={name}
                    param={param}
                    value={paramValues[name] ?? ''}
                    error={fieldErrors[name]}
                    onChange={handleParamChange}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Advanced: Context overrides (collapsible) */}
          <section aria-label="Advanced options">
            <button
              type="button"
              className={cn(
                'flex w-full items-center gap-1.5 text-xs font-semibold uppercase tracking-wider',
                'text-muted-foreground transition-colors hover:text-foreground',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded'
              )}
              aria-expanded={advancedOpen}
              aria-controls="advanced-section"
              onClick={() => setAdvancedOpen((prev) => !prev)}
            >
              {advancedOpen ? (
                <ChevronDown className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 flex-shrink-0" aria-hidden="true" />
              )}
              Advanced
            </button>

            {advancedOpen && (
              <div id="advanced-section" className="mt-3 space-y-3">
                <div className="space-y-1.5">
                  <Label htmlFor="context-overrides" className="text-sm font-medium">
                    Context module overrides
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    Override the context modules injected into this execution. Enter module
                    references separated by commas (e.g.{' '}
                    <code className="rounded bg-muted px-1 py-0.5 font-mono text-[11px]">
                      ctx:domain-knowledge
                    </code>
                    ).
                  </p>
                  <Textarea
                    id="context-overrides"
                    value={contextOverrides}
                    onChange={(e) => setContextOverrides(e.target.value)}
                    placeholder="ctx:module-name, ctx:another-module"
                    rows={2}
                    className="resize-none font-mono text-sm"
                  />
                </div>
              </div>
            )}
          </section>

          {/* Inline submission error */}
          {submitError && (
            <div
              role="alert"
              className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive"
            >
              <TriangleAlert className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden="true" />
              <p>{submitError}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <DialogFooter className="mt-4 flex-row gap-2 sm:justify-end">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isRunning}
            className="min-w-[80px]"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={handleRun}
            disabled={isRunning || !workflow}
            className={cn(
              'min-w-[100px] gap-1.5',
              'bg-indigo-600 hover:bg-indigo-700 focus-visible:ring-indigo-500 text-white',
              'dark:bg-indigo-500 dark:hover:bg-indigo-600'
            )}
            aria-label={workflow ? `Run workflow: ${workflow.name}` : 'Run workflow'}
          >
            {isRunning ? (
              <>
                <span
                  className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white"
                  aria-hidden="true"
                />
                Starting…
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-current" aria-hidden="true" />
                Run
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
