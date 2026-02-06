/**
 * EffectiveContextPreview Component (UI-4.6)
 *
 * A read-only modal previewing a generated context pack with rendered markdown,
 * token budget utilization bar, included item summary, and copy-to-clipboard
 * action. Uses shadcn Dialog for accessible modal behavior with focus trapping
 * and Escape dismissal.
 */

'use client';

import * as React from 'react';
import { useState, useCallback } from 'react';
import {
  Copy,
  Check,
  RefreshCw,
  Loader2,
  FileText,
  ChevronDown,
} from 'lucide-react';
import type { ContextPackGenerateResponse } from '@/sdk/models/ContextPackGenerateResponse';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { cn } from '@/lib/utils';
import { MemoryTypeBadge } from './memory-type-badge';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface EffectiveContextPreviewProps {
  /** Whether the dialog is open. */
  open: boolean;
  /** Callback to control open state. */
  onOpenChange: (open: boolean) => void;
  /** Generated context pack data. Null when not yet generated. */
  data?: ContextPackGenerateResponse | null;
  /** Whether context pack generation is in progress. */
  isLoading?: boolean;
  /** Callback to regenerate the context pack. */
  onRegenerate?: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type UtilizationTier = 'normal' | 'warning' | 'critical';

/**
 * Classify utilization (0-1) into a visual tier.
 *
 * - normal:   < 70% -- green
 * - warning:  70-90% -- yellow/amber
 * - critical: > 90% -- red
 */
function getUtilizationTier(utilization: number): UtilizationTier {
  if (utilization >= 0.9) return 'critical';
  if (utilization >= 0.7) return 'warning';
  return 'normal';
}

/** Progress bar color class by utilization tier. */
function getUtilizationBarColor(tier: UtilizationTier): string {
  switch (tier) {
    case 'normal':
      return 'bg-emerald-500';
    case 'warning':
      return 'bg-amber-500';
    case 'critical':
      return 'bg-red-500';
  }
}

/** Text color classes by utilization tier. */
function getUtilizationTextColor(tier: UtilizationTier): string {
  switch (tier) {
    case 'normal':
      return 'text-emerald-700 dark:text-emerald-400';
    case 'warning':
      return 'text-amber-700 dark:text-amber-400';
    case 'critical':
      return 'text-red-700 dark:text-red-400';
  }
}

/** Format a token count with comma separators. */
function formatTokenCount(count: number): string {
  return count.toLocaleString();
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

/**
 * TokenBudgetBar -- visual progress bar showing token budget utilization
 * with color-coded feedback.
 */
function TokenBudgetBar({
  totalTokens,
  budgetTokens,
  utilization,
  itemsIncluded,
  itemsAvailable,
}: {
  totalTokens: number;
  budgetTokens: number;
  utilization: number;
  itemsIncluded: number;
  itemsAvailable: number;
}) {
  const tier = getUtilizationTier(utilization);
  const percent = Math.round(utilization * 100);
  const barColor = getUtilizationBarColor(tier);
  const textColor = getUtilizationTextColor(tier);

  return (
    <div className="space-y-2 rounded-lg border bg-muted/30 p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Token Budget</span>
        <span className={cn('text-sm font-semibold', textColor)}>
          {formatTokenCount(totalTokens)} / {formatTokenCount(budgetTokens)}{' '}
          tokens ({percent}%)
        </span>
      </div>
      <div
        className="relative h-2.5 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-valuenow={totalTokens}
        aria-valuemin={0}
        aria-valuemax={budgetTokens}
        aria-label={`Token budget: ${formatTokenCount(totalTokens)} of ${formatTokenCount(budgetTokens)} tokens used (${percent}%)`}
      >
        <div
          className={cn(
            'h-full rounded-full transition-all duration-300',
            barColor
          )}
          style={{ width: `${Math.min(percent, 100)}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        {itemsIncluded} of {itemsAvailable} items included
      </p>
    </div>
  );
}

/**
 * ItemSummaryList -- collapsible list of included context pack items
 * showing type, content snippet, confidence, and token count.
 */
function ItemSummaryList({
  items,
}: {
  items: Array<Record<string, any>>;
}) {
  const [isOpen, setIsOpen] = useState(false);

  if (items.length === 0) {
    return null;
  }

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger asChild>
        <button
          className="flex w-full items-center justify-between py-2 text-sm font-semibold hover:text-foreground transition-colors"
          aria-expanded={isOpen}
          aria-label="Toggle included items list"
        >
          <span className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
            Included Items ({items.length})
          </span>
          <ChevronDown
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform duration-200',
              isOpen && 'rotate-180'
            )}
            aria-hidden="true"
          />
        </button>
      </CollapsibleTrigger>
      <CollapsibleContent>
        <div className="mt-1 space-y-2">
          {items.map((item, index) => {
            const content = typeof item.content === 'string' ? item.content : '';
            const snippet =
              content.length > 120 ? content.slice(0, 120) + '...' : content;
            const confidence =
              typeof item.confidence === 'number'
                ? Math.round(item.confidence * 100)
                : null;
            const tokens =
              typeof item.tokens === 'number' ? item.tokens : null;
            const itemType = typeof item.type === 'string' ? item.type : null;
            const itemId =
              typeof item.id === 'string' ? item.id : `item-${index}`;

            return (
              <div
                key={itemId}
                className="flex items-start gap-3 rounded-md border bg-background p-3"
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {itemType && <MemoryTypeBadge type={itemType} />}
                    {confidence !== null && (
                      <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                        {confidence}%
                      </Badge>
                    )}
                    {tokens !== null && (
                      <span className="text-[10px] text-muted-foreground">
                        {formatTokenCount(tokens)} tokens
                      </span>
                    )}
                  </div>
                  {snippet && (
                    <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
                      {snippet}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

/**
 * EffectiveContextPreview -- read-only modal displaying a generated context
 * pack with markdown rendering, token budget visualization, and item summary.
 *
 * @example
 * ```tsx
 * <EffectiveContextPreview
 *   open={showPreview}
 *   onOpenChange={setShowPreview}
 *   data={contextPackData}
 *   isLoading={isGenerating}
 *   onRegenerate={handleRegenerate}
 * />
 * ```
 */
export function EffectiveContextPreview({
  open,
  onOpenChange,
  data,
  isLoading = false,
  onRegenerate,
}: EffectiveContextPreviewProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    if (!data?.markdown) return;

    try {
      await navigator.clipboard.writeText(data.markdown);
      setCopied(true);
      // Reset after 2 seconds
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for environments without clipboard API
      const textarea = document.createElement('textarea');
      textarea.value = data.markdown;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      } catch {
        // Silently fail -- user can manually select and copy
      }
      document.body.removeChild(textarea);
    }
  }, [data?.markdown]);

  // Reset copied state when dialog closes
  React.useEffect(() => {
    if (!open) {
      setCopied(false);
    }
  }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col gap-0 p-0">
        {/* ----------------------------------------------------------------- */}
        {/* Header                                                            */}
        {/* ----------------------------------------------------------------- */}
        <div className="px-6 pt-6 pb-4">
          <DialogHeader>
            <DialogTitle>Effective Context Preview</DialogTitle>
            <DialogDescription>
              Preview of the generated context pack with token budget
              utilization.
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* ----------------------------------------------------------------- */}
        {/* Body                                                              */}
        {/* ----------------------------------------------------------------- */}
        {isLoading ? (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16">
            <Loader2
              className="h-8 w-8 animate-spin text-muted-foreground"
              aria-hidden="true"
            />
            <p className="text-sm text-muted-foreground">
              Generating context pack...
            </p>
          </div>
        ) : data ? (
          <div className="flex flex-1 flex-col overflow-hidden">
            {/* Token Budget Bar */}
            <div className="px-6 pb-4">
              <TokenBudgetBar
                totalTokens={data.total_tokens}
                budgetTokens={data.budget_tokens}
                utilization={data.utilization}
                itemsIncluded={data.items_included}
                itemsAvailable={data.items_available}
              />
            </div>

            <Separator />

            {/* Markdown Content */}
            <ScrollArea className="flex-1 min-h-0" style={{ maxHeight: '40vh' }}>
              <div className="px-6 py-4">
                <pre
                  className={cn(
                    'whitespace-pre-wrap break-words rounded-lg border bg-muted/50 p-4',
                    'font-mono text-sm leading-relaxed',
                    'text-foreground'
                  )}
                >
                  {data.markdown}
                </pre>
              </div>
            </ScrollArea>

            <Separator />

            {/* Item Summary */}
            <div className="px-6 py-3">
              <ItemSummaryList items={data.items} />
            </div>
          </div>
        ) : (
          <div className="flex flex-1 flex-col items-center justify-center gap-3 py-16">
            <FileText
              className="h-8 w-8 text-muted-foreground"
              aria-hidden="true"
            />
            <p className="text-sm text-muted-foreground">
              No context pack data available. Generate one to preview.
            </p>
          </div>
        )}

        {/* ----------------------------------------------------------------- */}
        {/* Footer                                                            */}
        {/* ----------------------------------------------------------------- */}
        <div className="border-t px-6 py-4">
          <DialogFooter className="sm:justify-between">
            <div className="flex items-center gap-2">
              {data?.generated_at && (
                <span className="text-xs text-muted-foreground">
                  Generated{' '}
                  {new Date(data.generated_at).toLocaleString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {onRegenerate && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1.5"
                  onClick={onRegenerate}
                  disabled={isLoading}
                >
                  <RefreshCw
                    className={cn(
                      'h-3.5 w-3.5',
                      isLoading && 'animate-spin'
                    )}
                    aria-hidden="true"
                  />
                  Regenerate
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                className="gap-1.5"
                onClick={handleCopy}
                disabled={!data?.markdown || isLoading}
                aria-label={
                  copied
                    ? 'Copied to clipboard'
                    : 'Copy context pack to clipboard'
                }
              >
                {copied ? (
                  <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
                ) : (
                  <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                )}
                {copied ? 'Copied' : 'Copy'}
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={() => onOpenChange(false)}
              >
                Close
              </Button>
            </div>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
