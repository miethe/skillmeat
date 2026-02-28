'use client';

/**
 * BuilderSidebar — Right-side metadata panel for the workflow builder canvas.
 *
 * A fixed-width (w-80 / 320px) panel that sticks to the right edge of the
 * builder layout on desktop and collapses off-canvas on mobile. Renders four
 * collapsible sections covering workflow identity, tags, global context
 * injection, and runtime execution settings.
 *
 * All state is lifted: every field fires a discrete onChange callback so the
 * parent canvas can maintain a single source-of-truth form state.
 *
 * Layout contract:
 *   - Parent must give the sidebar `h-full` or equivalent so the sticky
 *     positioning works correctly within the builder's flex row.
 *   - On mobile (< md breakpoint) the sidebar is hidden via `hidden md:flex`.
 *     Parent is responsible for surfacing an "Edit metadata" sheet/drawer
 *     if mobile editing is required.
 *
 * @example
 * ```tsx
 * <BuilderSidebar
 *   name={workflow.name}
 *   description={workflow.description ?? ''}
 *   tags={workflow.tags}
 *   contextPolicy={contextPolicy}
 *   parameters={Object.values(workflow.parameters)}
 *   onNameChange={(n) => setWorkflow((w) => ({ ...w, name: n }))}
 *   onDescriptionChange={(d) => setWorkflow((w) => ({ ...w, description: d }))}
 *   onTagsChange={(t) => setWorkflow((w) => ({ ...w, tags: t }))}
 *   onContextPolicyChange={setContextPolicy}
 *   onParametersChange={setParameters}
 * />
 * ```
 */

import * as React from 'react';
import {
  AlignLeft,
  ChevronDown,
  Code2,
  Cpu,
  Layers,
  Settings2,
  Tag,
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Separator } from '@/components/ui/separator';
import { TagEditor } from '@/components/shared/tag-editor';
import { ContextModulePicker } from '@/components/shared/context-module-picker';
import { cn } from '@/lib/utils';
import type { ContextPolicy, WorkflowParameter } from '@/types/workflow';

// ============================================================================
// Types
// ============================================================================

export interface BuilderSidebarProps {
  // ── Field values ──────────────────────────────────────────────────────────
  name: string;
  description: string;
  tags: string[];
  contextPolicy: ContextPolicy;
  parameters: WorkflowParameter[];

  // ── Change callbacks ──────────────────────────────────────────────────────
  onNameChange: (name: string) => void;
  onDescriptionChange: (description: string) => void;
  onTagsChange: (tags: string[]) => void;
  onContextPolicyChange: (policy: ContextPolicy) => void;
  onParametersChange: (params: WorkflowParameter[]) => void;

  // ── Layout ────────────────────────────────────────────────────────────────
  className?: string;
}

// ============================================================================
// Section — collapsible fieldset with icon + title header
// ============================================================================

interface SectionProps {
  id: string;
  title: string;
  icon: React.ElementType;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

function Section({ id, title, icon: Icon, defaultOpen = true, children }: SectionProps) {
  const [open, setOpen] = React.useState(defaultOpen);
  const contentId = `builder-sidebar-section-${id}`;
  const headingId = `builder-sidebar-heading-${id}`;

  return (
    <div>
      {/* ── Section header ─────────────────────────────────────────────── */}
      <button
        type="button"
        id={headingId}
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((prev) => !prev)}
        className={cn(
          'group flex w-full items-center gap-2 px-4 py-2.5',
          'text-left',
          'transition-colors hover:bg-muted/40',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset'
        )}
      >
        {/* Icon tick mark — left-rail accent */}
        <span
          className={cn(
            'flex h-5 w-5 shrink-0 items-center justify-center rounded',
            'bg-muted text-muted-foreground',
            'transition-colors group-hover:bg-muted/80'
          )}
          aria-hidden="true"
        >
          <Icon className="h-3 w-3" />
        </span>

        <span className="flex-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-muted-foreground/80">
          {title}
        </span>

        <ChevronDown
          className={cn(
            'h-3.5 w-3.5 shrink-0 text-muted-foreground/50 transition-transform duration-200',
            open && 'rotate-180'
          )}
          aria-hidden="true"
        />
      </button>

      {/* ── Section body ───────────────────────────────────────────────── */}
      <div
        id={contentId}
        role="region"
        aria-labelledby={headingId}
        hidden={!open}
      >
        <div className="space-y-4 px-4 pb-4 pt-1">
          {children}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Field — label + control wrapper
// ============================================================================

interface FieldProps {
  id: string;
  label: string;
  hint?: string;
  children: React.ReactNode;
}

function Field({ id, label, hint, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <Label
        htmlFor={id}
        className="text-xs font-medium leading-none text-foreground/80"
      >
        {label}
      </Label>
      {children}
      {hint && (
        <p className="text-[11px] leading-snug text-muted-foreground">{hint}</p>
      )}
    </div>
  );
}

// ============================================================================
// ToggleRow — Switch with label + description in a bordered card row
// ============================================================================

interface ToggleRowProps {
  id: string;
  label: string;
  description: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

function ToggleRow({ id, label, description, checked, onCheckedChange }: ToggleRowProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-3 rounded-md border px-3 py-2.5',
        'transition-colors',
        checked
          ? 'border-border bg-muted/20'
          : 'border-border/50 bg-transparent'
      )}
    >
      <div className="min-w-0 space-y-0.5">
        <Label
          htmlFor={id}
          className="cursor-pointer text-xs font-medium leading-none"
        >
          {label}
        </Label>
        <p className="text-[11px] leading-snug text-muted-foreground">
          {description}
        </p>
      </div>
      <Switch
        id={id}
        checked={checked}
        onCheckedChange={onCheckedChange}
        aria-label={label}
        className="shrink-0"
      />
    </div>
  );
}

// ============================================================================
// ParameterList — read-only summary of declared WorkflowParameters
// ============================================================================

interface ParameterListProps {
  parameters: WorkflowParameter[];
}

function ParameterList({ parameters }: ParameterListProps) {
  if (parameters.length === 0) {
    return (
      <p className="rounded-md border border-dashed border-border/60 px-3 py-4 text-center text-[11px] text-muted-foreground">
        No parameters declared
      </p>
    );
  }

  return (
    <ul
      className="space-y-1.5"
      aria-label="Workflow parameters"
    >
      {parameters.map((param, index) => (
        <li
          key={index}
          className={cn(
            'flex items-start gap-2 rounded-md border border-border/50 px-2.5 py-2',
            'bg-muted/20'
          )}
        >
          <span
            className={cn(
              'mt-0.5 shrink-0 rounded px-1 py-px',
              'font-mono text-[10px] font-medium leading-none',
              'bg-muted text-muted-foreground'
            )}
            aria-label={`Type: ${param.type}`}
          >
            {param.type}
          </span>
          <div className="min-w-0 flex-1">
            {param.description ? (
              <p className="truncate text-xs text-foreground/80">
                {param.description}
              </p>
            ) : (
              <p className="truncate text-xs text-muted-foreground italic">
                No description
              </p>
            )}
            {param.required && (
              <span className="text-[10px] text-amber-500 dark:text-amber-400">
                Required
              </span>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}

// ============================================================================
// BuilderSidebar — Main component
// ============================================================================

export function BuilderSidebar({
  name,
  description,
  tags,
  contextPolicy,
  parameters,
  onNameChange,
  onDescriptionChange,
  onTagsChange,
  onContextPolicyChange,
  onParametersChange: _onParametersChange,
  className,
}: BuilderSidebarProps) {
  // ── Context policy helpers ─────────────────────────────────────────────────
  const handleModulesChange = React.useCallback(
    (modules: string[]) => {
      onContextPolicyChange({ ...contextPolicy, modules });
    },
    [contextPolicy, onContextPolicyChange]
  );

  const handleInheritGlobalChange = React.useCallback(
    (inheritGlobal: boolean) => {
      onContextPolicyChange({ ...contextPolicy, inheritGlobal });
    },
    [contextPolicy, onContextPolicyChange]
  );

  // ── Settings state (local — not yet in ContextPolicy; parent wires via
  //    onContextPolicyChange overloads or a separate prop in future)
  const [stopOnFirstFailure, setStopOnFirstFailure] = React.useState(false);
  const [allowRuntimeOverrides, setAllowRuntimeOverrides] = React.useState(false);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <aside
      aria-label="Workflow metadata"
      className={cn(
        // Base layout — hidden on mobile, fixed-width column on desktop
        'hidden md:flex flex-col',
        'w-80 shrink-0',
        // Positioning — sticky within the builder's flex row
        'sticky top-0 h-screen',
        // Visual treatment — subtly distinct from canvas
        'border-l border-border/70 bg-background',
        className
      )}
    >
      {/* ── Sidebar header ──────────────────────────────────────────────────── */}
      <div
        className={cn(
          'flex shrink-0 items-center gap-2 px-4 py-3',
          'border-b border-border/70',
          // Subtle ruled-grid background — industrial precision aesthetic
          'bg-[repeating-linear-gradient(90deg,transparent,transparent_calc(100%-1px),hsl(var(--border)/0.3)_calc(100%-1px))] bg-[length:24px_100%]',
          'bg-muted/20'
        )}
      >
        <Settings2
          className="h-4 w-4 text-muted-foreground/60"
          aria-hidden="true"
        />
        <h2 className="text-xs font-semibold uppercase tracking-[0.1em] text-muted-foreground/70">
          Properties
        </h2>
      </div>

      {/* ── Scrollable content area ─────────────────────────────────────────── */}
      <div
        className="flex-1 overflow-y-auto overscroll-contain"
        // Smooth scrolling for keyboard navigation
        style={{ scrollbarGutter: 'stable' }}
      >
        <div className="space-y-0 py-1">

          {/* ================================================================ */}
          {/* Section 1 — Metadata (Name + Description)                        */}
          {/* ================================================================ */}
          <Section id="metadata" title="Metadata" icon={AlignLeft}>
            <Field id="workflow-name" label="Name">
              <Input
                id="workflow-name"
                value={name}
                onChange={(e) => onNameChange(e.target.value)}
                placeholder="My Workflow"
                autoComplete="off"
                className="h-8 text-sm"
                aria-required="true"
              />
            </Field>

            <Field id="workflow-description" label="Description">
              <Textarea
                id="workflow-description"
                value={description}
                onChange={(e) => onDescriptionChange(e.target.value)}
                placeholder="What does this workflow accomplish?"
                rows={3}
                className="resize-none text-sm leading-relaxed"
              />
            </Field>
          </Section>

          <Separator className="mx-0 opacity-50" />

          {/* ================================================================ */}
          {/* Section 2 — Tags                                                  */}
          {/* ================================================================ */}
          <Section id="tags" title="Tags" icon={Tag}>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium leading-none text-foreground/80">
                Workflow tags
              </Label>
              <TagEditor
                tags={tags}
                onTagsChange={onTagsChange}
                availableTags={[]}
                className="min-h-[2rem]"
              />
              <p className="text-[11px] leading-snug text-muted-foreground">
                Tags help filter and organise workflows in the library.
              </p>
            </div>
          </Section>

          <Separator className="mx-0 opacity-50" />

          {/* ================================================================ */}
          {/* Section 3 — Global Context                                        */}
          {/* ================================================================ */}
          <Section id="global-context" title="Global Context" icon={Layers} defaultOpen={true}>
            <div className="space-y-3">
              <ContextModulePicker
                label="Global modules"
                value={contextPolicy.modules}
                onChange={handleModulesChange}
                placeholder="Select context modules..."
              />

              <ToggleRow
                id="inherit-parent-context"
                label="Inherit parent context"
                description="Include context modules from the parent workflow or project scope."
                checked={contextPolicy.inheritGlobal}
                onCheckedChange={handleInheritGlobalChange}
              />
            </div>
          </Section>

          <Separator className="mx-0 opacity-50" />

          {/* ================================================================ */}
          {/* Section 4 — Settings                                              */}
          {/* ================================================================ */}
          <Section id="settings" title="Settings" icon={Cpu}>
            <div className="space-y-2">
              <ToggleRow
                id="stop-on-first-failure"
                label="Stop on first failure"
                description="Halt the entire workflow when any stage fails, rather than continuing."
                checked={stopOnFirstFailure}
                onCheckedChange={setStopOnFirstFailure}
              />

              <ToggleRow
                id="allow-runtime-overrides"
                label="Allow runtime parameter overrides"
                description="Callers may supply parameter values at execution time."
                checked={allowRuntimeOverrides}
                onCheckedChange={setAllowRuntimeOverrides}
              />
            </div>
          </Section>

          <Separator className="mx-0 opacity-50" />

          {/* ================================================================ */}
          {/* Section 5 — Parameters (read-only summary)                        */}
          {/* ================================================================ */}
          <Section id="parameters" title="Parameters" icon={Code2} defaultOpen={false}>
            <ParameterList parameters={parameters} />
            <p className="text-[11px] leading-snug text-muted-foreground">
              Parameters are declared in the SWDL definition and resolved at
              execution time via{' '}
              <code className="rounded bg-muted px-1 font-mono text-[10px]">
                {'${{ parameters.<name> }}'}
              </code>
              .
            </p>
          </Section>

        </div>
      </div>

      {/* ── Footer — wordmark / version stamp ─────────────────────────────── */}
      <div
        className={cn(
          'shrink-0 border-t border-border/50',
          'px-4 py-2',
          'flex items-center justify-between',
          'bg-muted/10'
        )}
        aria-hidden="true"
      >
        <span className="font-mono text-[10px] text-muted-foreground/40 tracking-widest uppercase">
          Workflow Builder
        </span>
        <span className="h-1.5 w-1.5 rounded-full bg-emerald-500/60" title="Connected" />
      </div>
    </aside>
  );
}

export default BuilderSidebar;
