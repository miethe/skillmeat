'use client';

/**
 * ContextPackGenerator Component
 *
 * Provides the full context-pack generation workflow: module selection,
 * token-budget configuration, optional filters, preview, and generation.
 *
 * Connects ContextModulesTab data with the pack preview/generate mutations,
 * displaying inline preview results and triggering the EffectiveContextPreview
 * modal for full generated output.
 */

import { useState, useCallback, useMemo } from 'react';
import {
  Package,
  Eye,
  Loader2,
  Copy,
  Check,
  ChevronDown,
  SlidersHorizontal,
  Zap,
  FileText,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Progress } from '@/components/ui/progress';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import {
  useContextModules,
  usePreviewContextPack,
  useGenerateContextPack,
} from '@/hooks';
import { MemoryTypeBadge } from './memory-type-badge';
import { EffectiveContextPreview } from './effective-context-preview';
import { getConfidenceTier, getConfidenceColorClasses } from './memory-utils';
import type { ContextPackPreviewResponse } from '@/sdk/models/ContextPackPreviewResponse';
import type { ContextPackGenerateResponse } from '@/sdk/models/ContextPackGenerateResponse';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const BUDGET_PRESETS = [1000, 2000, 4000, 8000, 16000] as const;

const BUDGET_PRESET_LABELS: Record<number, string> = {
  1000: '1K',
  2000: '2K',
  4000: '4K',
  8000: '8K',
  16000: '16K',
};

const MEMORY_TYPE_OPTIONS = [
  { value: 'constraint', label: 'Constraints' },
  { value: 'decision', label: 'Decisions' },
  { value: 'fix', label: 'Fixes' },
  { value: 'pattern', label: 'Patterns' },
  { value: 'learning', label: 'Learnings' },
] as const;

const MIN_BUDGET = 100;
const MAX_BUDGET = 100000;
const DEFAULT_BUDGET = 4000;

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ContextPackGeneratorProps {
  /** Project ID for querying modules and generating packs. */
  projectId: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * ContextPackGenerator -- full pack generation workflow.
 *
 * Configuration panel at top (module selector, budget, filters), action
 * buttons in the middle, and preview/results displayed below.
 *
 * @example
 * ```tsx
 * <ContextPackGenerator projectId="proj_123" />
 * ```
 */
export function ContextPackGenerator({ projectId }: ContextPackGeneratorProps) {
  // ---- Local State ----
  const [selectedModuleId, setSelectedModuleId] = useState<string>('__all__');
  const [budget, setBudget] = useState<number>(DEFAULT_BUDGET);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [minConfidence, setMinConfidence] = useState<number>(0);
  const [previewData, setPreviewData] = useState<ContextPackPreviewResponse | null>(null);
  const [generateData, setGenerateData] = useState<ContextPackGenerateResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [showEffectivePreview, setShowEffectivePreview] = useState(false);

  // ---- Queries ----
  const { data: modulesData, isLoading: modulesLoading } = useContextModules(projectId);

  // ---- Mutations ----
  const previewMutation = usePreviewContextPack({
    onSuccess: (data) => {
      setPreviewData(data);
      // Clear any previous generation data when a new preview is done
      setGenerateData(null);
    },
  });

  const generateMutation = useGenerateContextPack({
    onSuccess: (data) => {
      setGenerateData(data);
      setShowEffectivePreview(true);
    },
  });

  // ---- Derived ----
  const modules = useMemo(() => modulesData?.items ?? [], [modulesData]);

  const buildRequestBody = useCallback(() => {
    const filters: Record<string, unknown> = {};
    if (selectedTypes.size > 0) {
      filters.type = Array.from(selectedTypes);
    }
    if (minConfidence > 0) {
      filters.min_confidence = minConfidence;
    }

    return {
      module_id: selectedModuleId === '__all__' ? undefined : selectedModuleId,
      budget_tokens: budget,
      filters: Object.keys(filters).length > 0 ? filters : undefined,
    };
  }, [selectedModuleId, budget, selectedTypes, minConfidence]);

  // ---- Handlers ----
  const handlePreview = useCallback(() => {
    previewMutation.mutate({
      projectId,
      data: buildRequestBody(),
    });
  }, [projectId, buildRequestBody, previewMutation]);

  const handleGenerate = useCallback(() => {
    generateMutation.mutate({
      projectId,
      data: buildRequestBody(),
    });
  }, [projectId, buildRequestBody, generateMutation]);

  const handleBudgetChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    if (!Number.isNaN(val)) {
      setBudget(Math.max(MIN_BUDGET, Math.min(MAX_BUDGET, val)));
    }
  }, []);

  const handleTypeToggle = useCallback((type: string, checked: boolean) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(type);
      } else {
        next.delete(type);
      }
      return next;
    });
  }, []);

  const handleConfidenceChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    if (!Number.isNaN(val)) {
      setMinConfidence(Math.max(0, Math.min(1, val)));
    }
  }, []);

  const handleCopyMarkdown = useCallback(async () => {
    if (!generateData?.markdown) return;
    try {
      await navigator.clipboard.writeText(generateData.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available -- silent fail
    }
  }, [generateData]);

  const isPreviewLoading = previewMutation.isPending;
  const isGenerateLoading = generateMutation.isPending;
  const isAnyLoading = isPreviewLoading || isGenerateLoading;
  const utilizationPercent = previewData
    ? Math.round(previewData.utilization * 100)
    : generateData
      ? Math.round(generateData.utilization * 100)
      : 0;

  // We'll show the latest result data (preview or generate)
  const resultData = generateData ?? previewData;

  return (
    <div className="space-y-4">
      {/* ================================================================== */}
      {/* Configuration Card                                                  */}
      {/* ================================================================== */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Package className="h-4 w-4" aria-hidden="true" />
            Context Pack Generator
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* -------------------------------------------------------------- */}
          {/* Module Selector                                                  */}
          {/* -------------------------------------------------------------- */}
          <div className="space-y-1.5">
            <Label htmlFor="module-select">Context Module</Label>
            <Select
              value={selectedModuleId}
              onValueChange={setSelectedModuleId}
              disabled={modulesLoading}
            >
              <SelectTrigger id="module-select" className="w-full">
                <SelectValue placeholder="Select a module..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all__">All Memories</SelectItem>
                {modules.map((mod) => (
                  <SelectItem key={mod.id} value={mod.id}>
                    {mod.name}
                    {mod.description ? ` -- ${mod.description}` : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {modulesLoading && (
              <p className="text-xs text-muted-foreground">Loading modules...</p>
            )}
          </div>

          {/* -------------------------------------------------------------- */}
          {/* Token Budget                                                     */}
          {/* -------------------------------------------------------------- */}
          <div className="space-y-1.5">
            <Label htmlFor="budget-input">Token Budget</Label>
            <div className="flex items-center gap-2">
              <Input
                id="budget-input"
                type="number"
                min={MIN_BUDGET}
                max={MAX_BUDGET}
                value={budget}
                onChange={handleBudgetChange}
                className="h-8 w-28 text-sm"
                aria-label="Token budget"
              />
              {/* Preset buttons */}
              <div className="flex gap-1" role="group" aria-label="Budget presets">
                {BUDGET_PRESETS.map((preset) => (
                  <Button
                    key={preset}
                    variant={budget === preset ? 'default' : 'outline'}
                    size="sm"
                    className="h-8 px-2.5 text-xs"
                    onClick={() => setBudget(preset)}
                    aria-label={`Set budget to ${preset} tokens`}
                    aria-pressed={budget === preset}
                  >
                    {BUDGET_PRESET_LABELS[preset]}
                  </Button>
                ))}
              </div>
            </div>
            <p className="text-xs text-muted-foreground">
              Range: {MIN_BUDGET.toLocaleString()} - {MAX_BUDGET.toLocaleString()} tokens
            </p>
          </div>

          {/* -------------------------------------------------------------- */}
          {/* Collapsible Filters                                              */}
          {/* -------------------------------------------------------------- */}
          <Collapsible open={filtersOpen} onOpenChange={setFiltersOpen}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 gap-2 px-2 text-xs text-muted-foreground hover:text-foreground"
                aria-expanded={filtersOpen}
              >
                <SlidersHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
                Advanced Filters
                <ChevronDown
                  className={cn(
                    'h-3.5 w-3.5 transition-transform',
                    filtersOpen && 'rotate-180'
                  )}
                  aria-hidden="true"
                />
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent className="pt-2">
              <div className="rounded-md border bg-muted/30 p-3 space-y-3">
                {/* Memory Type Multi-select */}
                <div className="space-y-1.5">
                  <Label className="text-xs font-medium">Memory Types</Label>
                  <div className="flex flex-wrap gap-3">
                    {MEMORY_TYPE_OPTIONS.map((opt) => (
                      <label
                        key={opt.value}
                        className="flex items-center gap-1.5 text-sm cursor-pointer"
                      >
                        <Checkbox
                          checked={selectedTypes.has(opt.value)}
                          onCheckedChange={(checked) =>
                            handleTypeToggle(opt.value, checked === true)
                          }
                          aria-label={`Filter by ${opt.label}`}
                        />
                        {opt.label}
                      </label>
                    ))}
                  </div>
                  {selectedTypes.size === 0 && (
                    <p className="text-xs text-muted-foreground">All types included</p>
                  )}
                </div>

                <Separator />

                {/* Min Confidence */}
                <div className="space-y-1.5">
                  <Label htmlFor="min-confidence" className="text-xs font-medium">
                    Min Confidence
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="min-confidence"
                      type="number"
                      min={0}
                      max={1}
                      step={0.05}
                      value={minConfidence}
                      onChange={handleConfidenceChange}
                      className="h-8 w-24 text-sm"
                      aria-label="Minimum confidence threshold"
                    />
                    <span className="text-xs text-muted-foreground">
                      {minConfidence === 0 ? 'No minimum' : `>= ${minConfidence.toFixed(2)}`}
                    </span>
                  </div>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          <Separator />

          {/* -------------------------------------------------------------- */}
          {/* Action Buttons                                                   */}
          {/* -------------------------------------------------------------- */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreview}
              disabled={isAnyLoading}
              className="gap-2"
              aria-label="Preview context pack"
            >
              {isPreviewLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Eye className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              Preview
            </Button>
            <Button
              size="sm"
              onClick={handleGenerate}
              disabled={isAnyLoading}
              className="gap-2"
              aria-label="Generate context pack"
            >
              {isGenerateLoading ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
              ) : (
                <Zap className="h-3.5 w-3.5" aria-hidden="true" />
              )}
              Generate Pack
            </Button>

            {/* Copy Markdown -- only when generate data exists */}
            {generateData?.markdown && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyMarkdown}
                className="ml-auto gap-2"
                aria-label={copied ? 'Markdown copied' : 'Copy generated markdown'}
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-emerald-500" aria-hidden="true" />
                ) : (
                  <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                {copied ? 'Copied' : 'Copy Markdown'}
              </Button>
            )}
          </div>

          {/* Mutation error messages */}
          {previewMutation.isError && (
            <p className="text-sm text-destructive" role="alert">
              Preview failed: {previewMutation.error.message}
            </p>
          )}
          {generateMutation.isError && (
            <p className="text-sm text-destructive" role="alert">
              Generation failed: {generateMutation.error.message}
            </p>
          )}
        </CardContent>
      </Card>

      {/* ================================================================== */}
      {/* Results Section                                                      */}
      {/* ================================================================== */}
      {resultData ? (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" aria-hidden="true" />
              Pack Results
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* ------------------------------------------------------------ */}
            {/* Utilization Summary                                            */}
            {/* ------------------------------------------------------------ */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Token Utilization</span>
                <span className="font-medium">
                  {resultData.total_tokens.toLocaleString()} /{' '}
                  {resultData.budget_tokens.toLocaleString()} tokens
                </span>
              </div>
              <Progress
                value={utilizationPercent}
                className="h-2"
                aria-label={`${utilizationPercent}% of token budget used`}
              />
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{utilizationPercent}% utilized</span>
                <span>
                  {resultData.items_included} / {resultData.items_available} items included
                </span>
              </div>
            </div>

            <Separator />

            {/* ------------------------------------------------------------ */}
            {/* Items List                                                     */}
            {/* ------------------------------------------------------------ */}
            {resultData.items.length > 0 ? (
              <div className="space-y-1.5">
                <Label className="text-xs font-medium">
                  Included Items ({resultData.items_included})
                </Label>
                <div className="max-h-64 overflow-y-auto rounded-md border">
                  <ul className="divide-y" role="list" aria-label="Included memory items">
                    {resultData.items.map((item, idx) => (
                      <PreviewItem key={item.id ?? idx} item={item} />
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                <Info className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
                No items matched the current filters and budget.
              </div>
            )}

            {/* Generated at timestamp */}
            {generateData?.generated_at && (
              <p className="text-xs text-muted-foreground">
                Generated at: {new Date(generateData.generated_at).toLocaleString()}
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        /* ------------------------------------------------------------------ */
        /* Empty State                                                         */
        /* ------------------------------------------------------------------ */
        !isAnyLoading && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-8 text-center">
              <Package
                className="mb-3 h-10 w-10 text-muted-foreground/50"
                aria-hidden="true"
              />
              <p className="text-sm font-medium text-muted-foreground">
                No results yet
              </p>
              <p className="mt-1 text-xs text-muted-foreground/80">
                Configure a module and budget above, then click Preview or Generate Pack.
              </p>
            </CardContent>
          </Card>
        )
      )}

      {/* ================================================================== */}
      {/* Effective Context Preview Modal                                      */}
      {/* ================================================================== */}
      <EffectiveContextPreview
        open={showEffectivePreview}
        onOpenChange={setShowEffectivePreview}
        data={generateData}
        isLoading={isGenerateLoading}
        onRegenerate={handleGenerate}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// PreviewItem Sub-component
// ---------------------------------------------------------------------------

interface PreviewItemProps {
  item: Record<string, unknown>;
}

/**
 * Single row in the preview items list. Displays type badge, content snippet,
 * confidence, and token count.
 */
function PreviewItem({ item }: PreviewItemProps) {
  const type = (item.type as string) ?? 'unknown';
  const content = (item.content as string) ?? '';
  const confidence = typeof item.confidence === 'number' ? item.confidence : 0;
  const tokens = typeof item.tokens === 'number' ? item.tokens : 0;

  const tier = getConfidenceTier(confidence);
  const colors = getConfidenceColorClasses(tier);

  // Truncate content for display
  const snippet = content.length > 120 ? content.slice(0, 120) + '...' : content;

  return (
    <li className="flex items-start gap-3 px-3 py-2 text-sm">
      <div className="flex flex-shrink-0 flex-col items-start gap-1 pt-0.5">
        <MemoryTypeBadge type={type} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs text-foreground" title={content}>
          {snippet}
        </p>
      </div>
      <div className="flex flex-shrink-0 items-center gap-2">
        <Badge
          variant="outline"
          className={cn('px-1.5 py-0 text-[10px]', colors.text, colors.border)}
        >
          {(confidence * 100).toFixed(0)}%
        </Badge>
        <span className="text-xs text-muted-foreground tabular-nums">
          {tokens.toLocaleString()}t
        </span>
      </div>
    </li>
  );
}

