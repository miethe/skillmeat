'use client';

/**
 * StageEditor — Slide-over panel for editing a workflow stage's properties.
 *
 * Wraps SlideOverPanel (width='lg') with a structured form covering:
 *   - Basic Info: name, description, stage type, execution mode
 *   - Roles: primary agent (EntityPickerDialog single), supporting tools (EntityPickerDialog multi)
 *   - Context Policy: context modules (ContextModulePicker), inherit global switch
 *   - Advanced (collapsed): timeout seconds, max retries, failure action
 *
 * Form state is local; initialized from the `stage` prop on open.
 * Save is disabled when no changes have been made.
 *
 * @example
 * ```tsx
 * <StageEditor
 *   stage={selectedStage}
 *   open={isEditorOpen}
 *   onClose={() => setIsEditorOpen(false)}
 *   onSave={(updated) => handleStageSave(updated)}
 * />
 * ```
 */

import * as React from 'react';
import { ChevronDown, Package } from 'lucide-react';
import { SlideOverPanel } from '@/components/shared/slide-over-panel';
import {
  EntityPickerDialog,
  EntityPickerTrigger,
} from '@/components/shared/entity-picker-dialog';
import type { EntityPickerTab } from '@/components/shared/entity-picker-dialog';
import { useEntityPickerArtifacts } from '@/components/shared/entity-picker-adapter-hooks';
import { MiniArtifactCard } from '@/components/collection/mini-artifact-card';
import { ContextModulePicker } from '@/components/shared/context-module-picker';
import type { Artifact } from '@/types/artifact';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type {
  WorkflowStage,
  ExecutionMode,
  FailureAction,
  StageType,
} from '@/types/workflow';

// ============================================================================
// Local form state shape
//
// We extract a flat, UI-friendly subset of WorkflowStage so the form stays
// simple. onSave merges these fields back into the original stage object.
// ============================================================================

interface StageFormState {
  name: string;
  description: string;
  stageType: StageType;
  executionMode: ExecutionMode;
  /** UUID of the primary agent artifact */
  primaryAgentUuid: string;
  /** UUIDs of supporting tool artifacts */
  toolUuids: string[];
  /** Context module IDs */
  contextModuleIds: string[];
  /** Whether to inherit the global workflow context */
  inheritGlobal: boolean;
  /** Timeout in seconds */
  timeoutSeconds: number;
  /** Max retry attempts */
  maxRetries: number;
  failureAction: FailureAction;
}

// ============================================================================
// Helpers: extract / merge form state from WorkflowStage
// ============================================================================

function stageToFormState(stage: WorkflowStage): StageFormState {
  return {
    name: stage.name,
    description: stage.description ?? '',
    // stageType on the API object is RawStageType; map to frontend StageType
    stageType:
      stage.stageType === 'agent'
        ? 'standard'
        : stage.stageType === 'gate'
          ? 'gate'
          : 'checkpoint',
    executionMode: 'sequential', // WorkflowStage has no direct executionMode field; default
    primaryAgentUuid: stage.roles?.primary?.artifact
      ? (stage.roles.primary.artifact.split(':')[1] ?? '')
      : '',
    toolUuids: [], // tool UUIDs are not stored on stage directly; start empty
    contextModuleIds: stage.context?.modules ?? [],
    inheritGlobal: true,
    timeoutSeconds: stage.errorPolicy?.timeout
      ? parseDurationToSeconds(stage.errorPolicy.timeout)
      : 60,
    maxRetries: stage.errorPolicy?.retry?.maxAttempts
      ? stage.errorPolicy.retry.maxAttempts - 1
      : 0,
    failureAction:
      (stage.errorPolicy?.onFailure as FailureAction | undefined) ?? 'halt',
  };
}

function defaultFormState(): StageFormState {
  return {
    name: '',
    description: '',
    stageType: 'standard',
    executionMode: 'sequential',
    primaryAgentUuid: '',
    toolUuids: [],
    contextModuleIds: [],
    inheritGlobal: true,
    timeoutSeconds: 60,
    maxRetries: 0,
    failureAction: 'halt',
  };
}

/** Merges form state back into the stage, preserving all other fields. */
function mergeFormStateIntoStage(
  original: WorkflowStage,
  form: StageFormState
): WorkflowStage {
  const rawStageType =
    form.stageType === 'standard'
      ? 'agent'
      : form.stageType === 'gate'
        ? 'gate'
        : 'fan_out';

  const timeoutStr = form.timeoutSeconds > 0 ? `${form.timeoutSeconds}s` : undefined;

  return {
    ...original,
    name: form.name,
    description: form.description || undefined,
    stageType: rawStageType,
    roles: {
      primary: {
        artifact: form.primaryAgentUuid ? `agent:${form.primaryAgentUuid}` : (original.roles?.primary?.artifact ?? ''),
        model: original.roles?.primary?.model,
        instructions: original.roles?.primary?.instructions,
      },
      tools: form.toolUuids,
    },
    context: {
      modules: form.contextModuleIds,
      memory: original.context?.memory,
    },
    errorPolicy: {
      ...original.errorPolicy,
      timeout: timeoutStr,
      onFailure: form.failureAction === 'halt' ? 'halt' : 'continue',
      retry: {
        maxAttempts: form.maxRetries + 1,
        initialInterval: original.errorPolicy?.retry?.initialInterval ?? '30s',
        backoffMultiplier: original.errorPolicy?.retry?.backoffMultiplier ?? 2,
        maxInterval: original.errorPolicy?.retry?.maxInterval ?? '5m',
        nonRetryableErrors: original.errorPolicy?.retry?.nonRetryableErrors ?? [],
      },
    },
  };
}

/**
 * Parse a simple duration string (e.g. "30s", "5m", "1h") to seconds.
 * Falls back to 60 for unrecognised formats.
 */
function parseDurationToSeconds(duration: string): number {
  const match = duration.match(/^(\d+)(s|m|h)$/);
  if (!match || !match[1] || !match[2]) return 60;
  const value = parseInt(match[1], 10);
  switch (match[2]) {
    case 'm':
      return value * 60;
    case 'h':
      return value * 3600;
    default:
      return value;
  }
}

function statesAreEqual(a: StageFormState, b: StageFormState): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

// ============================================================================
// Collapsible Section
// ============================================================================

interface SectionProps {
  id: string;
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function Section({ id, title, defaultOpen = true, children }: SectionProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  const contentId = `section-content-${id}`;
  const headingId = `section-heading-${id}`;

  return (
    <div className="space-y-0">
      <button
        type="button"
        id={headingId}
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          'flex w-full items-center justify-between py-2',
          'text-left text-sm font-semibold text-foreground',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 rounded-sm'
        )}
      >
        <span>{title}</span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform duration-200',
            open && 'rotate-180'
          )}
          aria-hidden="true"
        />
      </button>

      <div
        id={contentId}
        role="region"
        aria-labelledby={headingId}
        hidden={!open}
      >
        <div className="space-y-4 pb-2">{children}</div>
      </div>
    </div>
  );
}

// ============================================================================
// Field row helpers
// ============================================================================

interface FieldProps {
  id: string;
  label: string;
  children: React.ReactNode;
  hint?: string;
}

function Field({ id, label, children, hint }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id} className="text-sm font-medium leading-none">
        {label}
      </Label>
      {children}
      {hint && (
        <p className="text-[11px] text-muted-foreground leading-snug">{hint}</p>
      )}
    </div>
  );
}

// ============================================================================
// Props
// ============================================================================

export interface StageEditorProps {
  /** Stage to edit. When null, the form defaults to an empty state. */
  stage: WorkflowStage | null;
  /** Controls panel visibility. */
  open: boolean;
  /** Called to close the panel without saving. */
  onClose: () => void;
  /**
   * Called with the updated stage when the user clicks Save.
   * Merges form state back into the original stage object.
   */
  onSave: (stage: WorkflowStage) => void;
}

// ============================================================================
// Main component
// ============================================================================

export function StageEditor({ stage, open, onClose, onSave }: StageEditorProps) {
  const [form, setForm] = React.useState<StageFormState>(defaultFormState);
  const [initialForm, setInitialForm] = React.useState<StageFormState>(defaultFormState);

  // Dialog open states for the two pickers
  const [primaryAgentDialogOpen, setPrimaryAgentDialogOpen] = React.useState(false);
  const [toolsDialogOpen, setToolsDialogOpen] = React.useState(false);

  // Accumulated name map: uuid → name, built up as the user browses/selects artifacts.
  // Used to display resolved names in the triggers without additional API calls.
  const resolvedNamesRef = React.useRef<Map<string, string>>(new Map());

  // Incrementing this state triggers a re-render so the trigger can pick up
  // names accumulated in resolvedNamesRef after a dialog closes.
  const [, setResolvedNamesVersion] = React.useState(0);

  // Re-initialise form whenever stage or open state changes
  React.useEffect(() => {
    const next = stage ? stageToFormState(stage) : defaultFormState();
    setForm(next);
    setInitialForm(next);
  }, [stage, open]);

  const hasChanges = !statesAreEqual(form, initialForm);

  // --------------------------------------------------------------------------
  // Helpers for partial updates
  // --------------------------------------------------------------------------

  function patch<K extends keyof StageFormState>(key: K, value: StageFormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // --------------------------------------------------------------------------
  // Artifact tab configs for EntityPickerDialog
  // --------------------------------------------------------------------------

  // Stable renderCard that captures artifact names into the ref for trigger display.
  // Using useCallback with an empty dep array so the tab config object is stable
  // across renders and does not cause infinite re-renders inside EntityPickerDialog.
  const renderAgentCard = React.useCallback((item: Artifact, _isSelected: boolean) => {
    resolvedNamesRef.current.set(item.uuid, item.name);
    return <MiniArtifactCard artifact={item} onClick={() => {}} />;
  }, []);

  const renderToolCard = React.useCallback((item: Artifact, _isSelected: boolean) => {
    resolvedNamesRef.current.set(item.uuid, item.name);
    return <MiniArtifactCard artifact={item} onClick={() => {}} />;
  }, []);

  const primaryAgentTabs: EntityPickerTab<Artifact>[] = React.useMemo(() => [{
    id: 'artifacts',
    label: 'Agents',
    icon: Package,
    useData: (params) => useEntityPickerArtifacts({ ...params, typeFilter: ['agent'] }),
    renderCard: renderAgentCard,
    getId: (item) => item.uuid,
  }], [renderAgentCard]);

  const supportingToolsTabs: EntityPickerTab<Artifact>[] = React.useMemo(() => [{
    id: 'artifacts',
    label: 'Tools',
    icon: Package,
    useData: (params) => useEntityPickerArtifacts({ ...params, typeFilter: ['skill', 'command', 'mcp'] }),
    renderCard: renderToolCard,
    getId: (item) => item.uuid,
    typeFilters: [
      { value: 'skill', label: 'Skills' },
      { value: 'command', label: 'Commands' },
      { value: 'mcp', label: 'MCP Servers' },
    ],
  }], [renderToolCard]);

  // --------------------------------------------------------------------------
  // Resolved display items for EntityPickerTrigger
  // --------------------------------------------------------------------------

  const resolvedNames = resolvedNamesRef.current;

  const primaryAgentItems: { id: string; name: string }[] = form.primaryAgentUuid
    ? [{ id: form.primaryAgentUuid, name: resolvedNames.get(form.primaryAgentUuid) ?? form.primaryAgentUuid.slice(0, 8) }]
    : [];

  const toolItems: { id: string; name: string }[] = form.toolUuids.map((uuid) => ({
    id: uuid,
    name: resolvedNames.get(uuid) ?? uuid.slice(0, 8),
  }));

  // --------------------------------------------------------------------------
  // Save handler
  // --------------------------------------------------------------------------

  function handleSave() {
    if (!stage) return;
    const updated = mergeFormStateIntoStage(stage, form);
    onSave(updated);
  }

  // --------------------------------------------------------------------------
  // Panel title
  // --------------------------------------------------------------------------

  const panelTitle = form.name.trim() ? `Edit Stage: ${form.name}` : 'Edit Stage';

  // --------------------------------------------------------------------------
  // Render
  // --------------------------------------------------------------------------

  return (
    <SlideOverPanel
      open={open}
      onClose={onClose}
      title={panelTitle}
      description="Configure stage settings, agent assignments, and execution policy."
      width="lg"
    >
      {/* ------------------------------------------------------------------ */}
      {/* Scrollable form body                                                 */}
      {/* ------------------------------------------------------------------ */}
      <div className="space-y-0 pb-4" aria-label="Stage editor form">

        {/* ---------------------------------------------------------------- */}
        {/* Section 1: Basic Info                                             */}
        {/* ---------------------------------------------------------------- */}
        <Section id="basic-info" title="Basic Info">
          <Field id="stage-name" label="Name">
            <Input
              id="stage-name"
              value={form.name}
              onChange={(e) => patch('name', e.target.value)}
              placeholder="e.g. Code Review"
              autoComplete="off"
            />
          </Field>

          <Field id="stage-description" label="Description">
            <Textarea
              id="stage-description"
              value={form.description}
              onChange={(e) => patch('description', e.target.value)}
              placeholder="What happens in this stage?"
              rows={3}
              className="resize-none"
            />
          </Field>

          <Field id="stage-type" label="Stage Type">
            <Select
              value={form.stageType}
              onValueChange={(v) => patch('stageType', v as StageType)}
            >
              <SelectTrigger id="stage-type" aria-label="Stage type">
                <SelectValue placeholder="Select type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="standard">Standard</SelectItem>
                <SelectItem value="gate">Gate</SelectItem>
                <SelectItem value="checkpoint">Checkpoint</SelectItem>
              </SelectContent>
            </Select>
          </Field>

          <Field id="execution-mode" label="Execution Mode">
            <Select
              value={form.executionMode}
              onValueChange={(v) => patch('executionMode', v as ExecutionMode)}
            >
              <SelectTrigger id="execution-mode" aria-label="Execution mode">
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sequential">Sequential</SelectItem>
                <SelectItem value="parallel">Parallel</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </Section>

        <Separator className="my-1" />

        {/* ---------------------------------------------------------------- */}
        {/* Section 2: Roles                                                  */}
        {/* ---------------------------------------------------------------- */}
        <Section id="roles" title="Roles">
          {/* UEPD-3.1: Primary Agent picker */}
          <div className="space-y-1.5">
            <EntityPickerTrigger
              label="Primary Agent"
              value={form.primaryAgentUuid}
              items={primaryAgentItems}
              mode="single"
              onClick={() => setPrimaryAgentDialogOpen(true)}
              placeholder="Select an agent..."
            />
            <EntityPickerDialog
              open={primaryAgentDialogOpen}
              onOpenChange={(open) => {
                setPrimaryAgentDialogOpen(open);
                if (!open) setResolvedNamesVersion((v) => v + 1);
              }}
              tabs={primaryAgentTabs}
              mode="single"
              value={form.primaryAgentUuid}
              onChange={(value) => {
                patch('primaryAgentUuid', value as string);
              }}
              title="Select Primary Agent"
              description="Choose the main agent for this stage."
            />
          </div>

          {/* UEPD-3.2: Supporting Tools picker */}
          <div className="space-y-1.5">
            <EntityPickerTrigger
              label="Supporting Tools"
              value={form.toolUuids}
              items={toolItems}
              mode="multi"
              onClick={() => setToolsDialogOpen(true)}
              onRemove={(id) => patch('toolUuids', form.toolUuids.filter((uuid) => uuid !== id))}
              placeholder="Add supporting tools..."
            />
            <EntityPickerDialog
              open={toolsDialogOpen}
              onOpenChange={(open) => {
                setToolsDialogOpen(open);
                if (!open) setResolvedNamesVersion((v) => v + 1);
              }}
              tabs={supportingToolsTabs}
              mode="multi"
              value={form.toolUuids}
              onChange={(value) => {
                patch('toolUuids', value as string[]);
              }}
              title="Select Supporting Tools"
              description="Choose skills, commands, and MCP servers available to this stage."
            />
          </div>
        </Section>

        <Separator className="my-1" />

        {/* ---------------------------------------------------------------- */}
        {/* Section 3: Context Policy                                         */}
        {/* ---------------------------------------------------------------- */}
        <Section id="context-policy" title="Context Policy">
          <ContextModulePicker
            label="Context Modules"
            value={form.contextModuleIds}
            onChange={(v) => patch('contextModuleIds', v)}
            placeholder="Select context modules..."
          />

          <div className="flex items-center justify-between rounded-md border border-input bg-muted/30 px-3 py-2.5">
            <div className="space-y-0.5">
              <Label
                htmlFor="inherit-global"
                className="text-sm font-medium leading-none cursor-pointer"
              >
                Inherit global context
              </Label>
              <p className="text-xs text-muted-foreground">
                Inject workflow-level context modules into this stage
              </p>
            </div>
            <Switch
              id="inherit-global"
              checked={form.inheritGlobal}
              onCheckedChange={(checked) => patch('inheritGlobal', checked)}
              aria-label="Inherit global context"
            />
          </div>
        </Section>

        <Separator className="my-1" />

        {/* ---------------------------------------------------------------- */}
        {/* Section 4: Advanced (collapsed by default)                        */}
        {/* ---------------------------------------------------------------- */}
        <Section id="advanced" title="Advanced" defaultOpen={false}>
          <Field
            id="timeout-seconds"
            label="Timeout (seconds)"
            hint="Maximum time allowed for this stage. 0 means no limit."
          >
            <Input
              id="timeout-seconds"
              type="number"
              min={0}
              value={form.timeoutSeconds}
              onChange={(e) =>
                patch('timeoutSeconds', Math.max(0, parseInt(e.target.value, 10) || 0))
              }
            />
          </Field>

          <Field
            id="max-retries"
            label="Max Retries"
            hint="Number of additional attempts after the first failure."
          >
            <Input
              id="max-retries"
              type="number"
              min={0}
              max={10}
              value={form.maxRetries}
              onChange={(e) =>
                patch(
                  'maxRetries',
                  Math.min(10, Math.max(0, parseInt(e.target.value, 10) || 0))
                )
              }
            />
          </Field>

          <Field id="failure-action" label="On Failure Action">
            <Select
              value={form.failureAction}
              onValueChange={(v) => patch('failureAction', v as FailureAction)}
            >
              <SelectTrigger id="failure-action" aria-label="On failure action">
                <SelectValue placeholder="Select action" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="halt">Halt Workflow</SelectItem>
                <SelectItem value="continue">Continue</SelectItem>
                <SelectItem value="retry_then_halt">Retry then Halt</SelectItem>
              </SelectContent>
            </Select>
          </Field>
        </Section>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Sticky footer — sticks to bottom of the scroll container.           */}
      {/* The negative mx/px values extend it edge-to-edge despite the panel  */}
      {/* wrapper's px-6 padding.                                             */}
      {/* ------------------------------------------------------------------ */}
      <div
        className={cn(
          'sticky bottom-0 -mx-6 -mb-4',
          'flex items-center justify-end gap-3',
          'border-t bg-background/95 backdrop-blur-sm px-6 py-4'
        )}
        aria-label="Stage editor actions"
      >
        <Button
          type="button"
          variant="ghost"
          onClick={onClose}
        >
          Cancel
        </Button>
        <Button
          type="button"
          disabled={!hasChanges || !form.name.trim()}
          onClick={handleSave}
          className="bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50"
        >
          Save
        </Button>
      </div>
    </SlideOverPanel>
  );
}

export default StageEditor;
