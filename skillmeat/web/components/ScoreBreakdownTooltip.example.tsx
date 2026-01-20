/**
 * ScoreBreakdownTooltip Usage Examples
 *
 * This file demonstrates common usage patterns for the ScoreBreakdownTooltip
 * component. These examples are for documentation purposes only.
 */

import { ScoreBreakdownTooltip } from '@/components/ScoreBreakdownTooltip';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

// Example breakdown data (typically from API response)
const exampleBreakdown = {
  dir_name_score: 50,
  manifest_score: 20,
  extensions_score: 10,
  parent_hint_score: 5,
  frontmatter_score: 0,
  depth_penalty: -10,
  raw_total: 75,
  normalized_score: 85,
};

/**
 * Example 1: Wrapping a confidence score badge
 *
 * Most common use case - show score breakdown when hovering over a confidence badge
 */
export function ConfidenceBadgeExample() {
  return (
    <ScoreBreakdownTooltip breakdown={exampleBreakdown}>
      <Badge variant="outline" className="cursor-help">
        85% confidence
      </Badge>
    </ScoreBreakdownTooltip>
  );
}

/**
 * Example 2: Custom placement (right side)
 *
 * Useful when the trigger is on the left side of the screen
 */
export function CustomPlacementExample() {
  return (
    <ScoreBreakdownTooltip breakdown={exampleBreakdown} side="right">
      <Button variant="ghost" size="sm" className="gap-2">
        <span className="text-muted-foreground">Score:</span>
        <span className="font-semibold">85</span>
      </Button>
    </ScoreBreakdownTooltip>
  );
}

/**
 * Example 3: Custom delay duration
 *
 * Longer delay for less intrusive tooltips
 */
export function CustomDelayExample() {
  return (
    <ScoreBreakdownTooltip breakdown={exampleBreakdown} delayDuration={500}>
      <span className="cursor-help text-sm text-muted-foreground underline decoration-dotted">
        View score breakdown
      </span>
    </ScoreBreakdownTooltip>
  );
}

/**
 * Example 4: In a table cell
 *
 * Common pattern for marketplace match listings
 */
export function TableCellExample() {
  return (
    <td className="text-center">
      <ScoreBreakdownTooltip breakdown={exampleBreakdown} side="top">
        <Badge
          variant={exampleBreakdown.normalized_score >= 70 ? 'default' : 'secondary'}
          className="cursor-help"
        >
          {exampleBreakdown.normalized_score}%
        </Badge>
      </ScoreBreakdownTooltip>
    </td>
  );
}

/**
 * Example 5: With icon trigger
 *
 * For compact displays where only an icon is shown
 */
export function IconTriggerExample() {
  return (
    <ScoreBreakdownTooltip breakdown={exampleBreakdown} side="right">
      <button
        className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-primary transition-colors hover:bg-primary/20"
        aria-label="View score breakdown"
      >
        <span className="text-xs font-semibold">{exampleBreakdown.normalized_score}</span>
      </button>
    </ScoreBreakdownTooltip>
  );
}

/**
 * Example 6: Custom tooltip content styling
 *
 * Override default max-width or padding
 */
export function CustomContentStyleExample() {
  return (
    <ScoreBreakdownTooltip breakdown={exampleBreakdown} className="max-w-md p-4">
      <Badge variant="outline" className="cursor-help">
        Detailed breakdown
      </Badge>
    </ScoreBreakdownTooltip>
  );
}

/**
 * Example 7: Integration with marketplace match card
 *
 * Realistic usage in a marketplace match listing
 */
export function MarketplaceMatchExample() {
  const match = {
    name: 'Example Skill',
    path: '/path/to/skill',
    confidence: 85,
    score_breakdown: exampleBreakdown,
  };

  return (
    <div className="flex items-center justify-between rounded-lg border p-4">
      <div>
        <h3 className="font-semibold">{match.name}</h3>
        <p className="text-sm text-muted-foreground">{match.path}</p>
      </div>
      <ScoreBreakdownTooltip breakdown={match.score_breakdown}>
        <Badge variant={match.confidence >= 70 ? 'default' : 'secondary'} className="cursor-help">
          {match.confidence}% match
        </Badge>
      </ScoreBreakdownTooltip>
    </div>
  );
}
