/**
 * Context Load Order Visualization Component
 *
 * Displays the loading order and token usage for context entities.
 * Shows specs (loaded first), then rules, then context (on-demand).
 * Helps users understand auto-load behavior and optimize token usage.
 */

'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { CheckCircle2, Circle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

interface LoadOrderEntity {
  id: string;
  name: string;
  type: 'spec_file' | 'rule_file' | 'context_file' | 'project_config' | 'progress_template';
  tokens: number;
  autoLoad: boolean;
}

export interface ContextLoadOrderProps {
  /** List of entities to display in load order */
  entities: LoadOrderEntity[];
}

// ============================================================================
// Sub-components
// ============================================================================

interface EntityLoadItemProps {
  entity: LoadOrderEntity;
}

function EntityLoadItem({ entity }: EntityLoadItemProps) {
  const Icon = entity.autoLoad ? CheckCircle2 : Circle;

  return (
    <div className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-muted/50 transition-colors">
      <div className="flex items-center gap-2 min-w-0 flex-1">
        <Icon
          className={cn(
            'h-3.5 w-3.5 flex-shrink-0',
            entity.autoLoad ? 'text-green-600' : 'text-muted-foreground'
          )}
        />
        <span className="text-sm truncate">{entity.name}</span>
      </div>
      <Badge variant="secondary" className="text-xs ml-2 flex-shrink-0">
        ~{entity.tokens}
      </Badge>
    </div>
  );
}

interface LoadPhaseProps {
  phase: number;
  title: string;
  description: string;
  entities: LoadOrderEntity[];
  variant?: 'default' | 'outline';
}

function LoadPhase({ phase, title, description, entities, variant = 'default' }: LoadPhaseProps) {
  const totalTokens = entities.reduce((sum, e) => sum + (e.autoLoad ? e.tokens : 0), 0);
  const autoLoadCount = entities.filter((e) => e.autoLoad).length;

  return (
    <div className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge variant={variant} className="flex-shrink-0">
            {phase}
          </Badge>
          <div className="min-w-0">
            <h4 className="text-sm font-medium">{title}</h4>
            <p className="text-xs text-muted-foreground">{description}</p>
          </div>
        </div>
        {autoLoadCount > 0 && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Badge variant="secondary" className="text-xs flex-shrink-0">
                  {totalTokens} tokens
                </Badge>
              </TooltipTrigger>
              <TooltipContent>
                <p>
                  {autoLoadCount} auto-load {autoLoadCount === 1 ? 'entity' : 'entities'}
                </p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>

      {entities.length === 0 ? (
        <div className="text-xs text-muted-foreground italic pl-8">No entities in this phase</div>
      ) : (
        <div className="pl-8 space-y-0.5">
          {entities.map((entity) => (
            <EntityLoadItem key={entity.id} entity={entity} />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * ContextLoadOrder - Visualizes entity load order and token usage
 *
 * Groups context entities by type and shows their loading sequence:
 * 1. Specs (auto-loaded first, highest priority)
 * 2. Rules (auto-loaded second, path-scoped)
 * 3. Context (on-demand, lowest priority)
 *
 * Displays token counts to help users optimize their auto-load configuration
 * and stay within recommended token budgets.
 *
 * @example
 * ```tsx
 * <ContextLoadOrder
 *   entities={[
 *     { id: '1', name: 'API Spec', type: 'spec_file', tokens: 500, autoLoad: true },
 *     { id: '2', name: 'Web Rules', type: 'rule_file', tokens: 300, autoLoad: true },
 *     { id: '3', name: 'Patterns', type: 'context_file', tokens: 800, autoLoad: false },
 *   ]}
 * />
 * ```
 *
 * @param props - ContextLoadOrderProps configuration
 * @returns Load order visualization component
 */
export function ContextLoadOrder({ entities }: ContextLoadOrderProps) {
  // Group entities by type for load order visualization
  const specs = entities.filter((e) => e.type === 'spec_file' || e.type === 'project_config');
  const rules = entities.filter((e) => e.type === 'rule_file');
  const context = entities.filter(
    (e) => e.type === 'context_file' || e.type === 'progress_template'
  );

  // Calculate total auto-load tokens
  const totalAutoLoadTokens = entities.reduce(
    (sum, e) => sum + (e.autoLoad ? e.tokens : 0),
    0
  );

  return (
    <Card className="p-4">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="font-semibold">Context Load Order</h3>
            <p className="text-sm text-muted-foreground">
              Entities load in priority order when auto-load is enabled
            </p>
          </div>
          <div className="text-right">
            <div className="text-sm font-medium">Total Auto-load</div>
            <div
              className={cn(
                'text-2xl font-bold',
                totalAutoLoadTokens > 2000 && 'text-destructive'
              )}
            >
              {totalAutoLoadTokens}
            </div>
            <div className="text-xs text-muted-foreground">tokens</div>
          </div>
        </div>

        {/* Load Phases */}
        <div className="space-y-4">
          <LoadPhase
            phase={1}
            title="Specs & Config"
            description="Auto-loaded first (highest priority)"
            entities={specs}
            variant="default"
          />

          <LoadPhase
            phase={2}
            title="Rules"
            description="Auto-loaded when path pattern matches"
            entities={rules}
            variant="default"
          />

          <LoadPhase
            phase={3}
            title="Context"
            description="On-demand only (manual loading)"
            entities={context}
            variant="outline"
          />
        </div>

        {/* Legend */}
        <div className="pt-2 border-t space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
            <span className="text-muted-foreground">Auto-load enabled (loads automatically)</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Circle className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Manual load (requires explicit loading)</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
