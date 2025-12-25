'use client';

import * as React from 'react';
import { ChevronDown } from 'lucide-react';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

/**
 * Score component configuration with display properties
 */
interface ScoreComponent {
  name: string;
  score: number;
  weight: number;
  color: string;
  description: string;
}

/**
 * Props for the ScoreBreakdown component
 */
export interface ScoreBreakdownProps {
  /**
   * Final composite confidence score (0-100)
   */
  confidence: number;
  /**
   * Source trustworthiness score (0-100)
   */
  trust: number;
  /**
   * User/community ratings + maintenance quality score (0-100)
   */
  quality: number;
  /**
   * Semantic relevance to query score (0-100)
   */
  match: number;
  /**
   * Weight configuration for each component
   * @default { trust: 0.25, quality: 0.25, match: 0.50 }
   */
  weights?: {
    trust: number;
    quality: number;
    match: number;
  };
  /**
   * Whether the breakdown is expanded by default
   * @default false
   */
  defaultExpanded?: boolean;
  /**
   * Additional CSS classes
   */
  className?: string;
}

/**
 * ScoreBreakdown Component
 *
 * Displays an expandable breakdown of the confidence score showing:
 * - Trust: Source trustworthiness (default 25% weight)
 * - Quality: User ratings + maintenance (default 25% weight)
 * - Match: Semantic relevance to query (default 50% weight)
 *
 * @example
 * ```tsx
 * <ScoreBreakdown
 *   confidence={92}
 *   trust={95}
 *   quality={87}
 *   match={92}
 *   defaultExpanded={false}
 * />
 * ```
 */
export function ScoreBreakdown({
  confidence,
  trust,
  quality,
  match,
  weights = { trust: 0.25, quality: 0.25, match: 0.50 },
  defaultExpanded = false,
  className,
}: ScoreBreakdownProps) {
  const [isOpen, setIsOpen] = React.useState(defaultExpanded);

  const components: ScoreComponent[] = [
    {
      name: 'Trust',
      score: trust,
      weight: weights.trust,
      color: 'bg-blue-500',
      description: 'Source trustworthiness',
    },
    {
      name: 'Quality',
      score: quality,
      weight: weights.quality,
      color: 'bg-green-500',
      description: 'User ratings + maintenance',
    },
    {
      name: 'Match',
      score: match,
      weight: weights.match,
      color: 'bg-purple-500',
      description: 'Relevance to your query',
    },
  ];

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen} className={className}>
      <CollapsibleTrigger
        className={cn(
          'flex items-center gap-2 text-sm font-medium transition-colors',
          'hover:text-primary focus-visible:outline-none focus-visible:ring-2',
          'focus-visible:ring-ring focus-visible:ring-offset-2 rounded-sm',
        )}
        aria-label={isOpen ? 'Hide score breakdown' : 'Show score breakdown'}
      >
        <ChevronDown
          className={cn('h-4 w-4 transition-transform duration-200', isOpen && 'rotate-180')}
          aria-hidden="true"
        />
        <span>Score breakdown</span>
      </CollapsibleTrigger>

      <CollapsibleContent className="mt-4 space-y-4">
        {components.map((component) => (
          <div key={component.name} className="space-y-1.5">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-foreground">{component.name}</span>
              <span className="tabular-nums">
                {component.score}{' '}
                <span className="text-muted-foreground">
                  ({Math.round(component.weight * 100)}%)
                </span>
              </span>
            </div>
            <Progress
              value={component.score}
              className="h-2"
              aria-label={`${component.name} score: ${component.score} out of 100`}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={component.score}
            />
            <p className="text-xs text-muted-foreground">{component.description}</p>
          </div>
        ))}

        <div className="border-t pt-3 text-xs text-muted-foreground font-mono">
          <span className="font-medium">Formula:</span> (T×{weights.trust}) + (Q×{weights.quality}) + (M×
          {weights.match}) = {confidence}%
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
