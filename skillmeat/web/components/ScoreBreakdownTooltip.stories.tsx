import type { Meta, StoryObj } from '@storybook/react';
import { ScoreBreakdownTooltip } from './ScoreBreakdownTooltip';
import { ScoreBadge } from './ScoreBadge';
import { Button } from '@/components/ui/button';

/**
 * ScoreBreakdownTooltip displays detailed score breakdowns
 * showing how confidence scores are calculated from various signals.
 *
 * ## Features
 * - Shows all scoring components (directory name, manifest, extensions, etc.)
 * - Displays penalties (depth penalty)
 * - Provides normalized score and raw total
 * - Keyboard accessible (hover and focus)
 * - Configurable placement and delay
 */
const meta = {
  title: 'Components/ScoreBreakdownTooltip',
  component: ScoreBreakdownTooltip,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: 'Tooltip component that displays detailed confidence score breakdowns with individual signal contributions.',
      },
    },
  },
  tags: ['autodocs'],
} satisfies Meta<typeof ScoreBreakdownTooltip>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Mock breakdown data for different score scenarios
 */
const highConfidenceBreakdown = {
  dir_name_score: 10,
  manifest_score: 20,
  extensions_score: 5,
  parent_hint_score: 15,
  frontmatter_score: 15,
  depth_penalty: 0,
  raw_total: 65,
  normalized_score: 100,
};

const mediumConfidenceBreakdown = {
  dir_name_score: 10,
  manifest_score: 20,
  extensions_score: 0,
  parent_hint_score: 0,
  frontmatter_score: 0,
  depth_penalty: -5,
  raw_total: 25,
  normalized_score: 38,
};

const withPenaltyBreakdown = {
  dir_name_score: 10,
  manifest_score: 20,
  extensions_score: 5,
  parent_hint_score: 15,
  frontmatter_score: 10,
  depth_penalty: -15,
  raw_total: 45,
  normalized_score: 69,
};

const lowConfidenceBreakdown = {
  dir_name_score: 0,
  manifest_score: 20,
  extensions_score: 0,
  parent_hint_score: 0,
  frontmatter_score: 0,
  depth_penalty: -10,
  raw_total: 10,
  normalized_score: 15,
};

const noSignalsBreakdown = {
  dir_name_score: 0,
  manifest_score: 0,
  extensions_score: 0,
  parent_hint_score: 0,
  frontmatter_score: 0,
  depth_penalty: -20,
  raw_total: -20,
  normalized_score: 0,
};

/**
 * Default story with ScoreBadge as trigger showing high confidence score
 */
export const Default: Story = {
  args: {
    breakdown: highConfidenceBreakdown,
  },
  render: (args) => (
    <div className="flex items-center gap-4 p-8">
      <span className="text-sm text-muted-foreground">Hover over the badge:</span>
      <ScoreBreakdownTooltip {...args}>
        <ScoreBadge score={args.breakdown.normalized_score} />
      </ScoreBreakdownTooltip>
    </div>
  ),
};

/**
 * Medium confidence score with partial signals
 */
export const MediumConfidence: Story = {
  args: {
    breakdown: mediumConfidenceBreakdown,
  },
  render: (args) => (
    <div className="flex items-center gap-4 p-8">
      <span className="text-sm text-muted-foreground">Medium confidence:</span>
      <ScoreBreakdownTooltip {...args}>
        <ScoreBadge score={args.breakdown.normalized_score} />
      </ScoreBreakdownTooltip>
    </div>
  ),
};

/**
 * Score with significant depth penalty
 */
export const WithLargePenalty: Story = {
  args: {
    breakdown: withPenaltyBreakdown,
  },
  render: (args) => (
    <div className="flex items-center gap-4 p-8">
      <span className="text-sm text-muted-foreground">With large penalty:</span>
      <ScoreBreakdownTooltip {...args}>
        <ScoreBadge score={args.breakdown.normalized_score} />
      </ScoreBreakdownTooltip>
    </div>
  ),
};

/**
 * Low confidence score with minimal signals
 */
export const LowConfidence: Story = {
  args: {
    breakdown: lowConfidenceBreakdown,
  },
  render: (args) => (
    <div className="flex items-center gap-4 p-8">
      <span className="text-sm text-muted-foreground">Low confidence:</span>
      <ScoreBreakdownTooltip {...args}>
        <ScoreBadge score={args.breakdown.normalized_score} />
      </ScoreBreakdownTooltip>
    </div>
  ),
};

/**
 * Zero score with no positive signals
 */
export const NoSignals: Story = {
  args: {
    breakdown: noSignalsBreakdown,
  },
  render: (args) => (
    <div className="flex items-center gap-4 p-8">
      <span className="text-sm text-muted-foreground">No signals detected:</span>
      <ScoreBreakdownTooltip {...args}>
        <ScoreBadge score={args.breakdown.normalized_score} />
      </ScoreBreakdownTooltip>
    </div>
  ),
};

/**
 * Tooltip on different sides (top, right, bottom, left)
 */
export const DifferentPlacements: Story = {
  render: () => (
    <div className="grid grid-cols-2 gap-8 p-16">
      <div className="flex flex-col items-center gap-2">
        <span className="text-xs text-muted-foreground">Top</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown} side="top">
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>

      <div className="flex flex-col items-center gap-2">
        <span className="text-xs text-muted-foreground">Right</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown} side="right">
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>

      <div className="flex flex-col items-center gap-2">
        <span className="text-xs text-muted-foreground">Bottom</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown} side="bottom">
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>

      <div className="flex flex-col items-center gap-2">
        <span className="text-xs text-muted-foreground">Left</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown} side="left">
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>
    </div>
  ),
};

/**
 * Custom delay durations
 */
export const CustomDelay: Story = {
  render: () => (
    <div className="flex flex-col gap-6 p-8">
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground w-32">No delay (0ms):</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown} delayDuration={0}>
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground w-32">Short (200ms):</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown} delayDuration={200}>
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground w-32">Default (500ms):</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown}>
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground w-32">Long (1000ms):</span>
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown} delayDuration={1000}>
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>
      </div>
    </div>
  ),
};

/**
 * Using Button as trigger element
 */
export const WithButton: Story = {
  args: {
    breakdown: highConfidenceBreakdown,
  },
  render: (args) => (
    <div className="flex items-center gap-4 p-8">
      <span className="text-sm text-muted-foreground">Button trigger:</span>
      <ScoreBreakdownTooltip {...args}>
        <Button variant="outline" size="sm">
          View Score Details
        </Button>
      </ScoreBreakdownTooltip>
    </div>
  ),
};

/**
 * Keyboard accessible - can be focused with Tab key
 */
export const KeyboardAccessible: Story = {
  args: {
    breakdown: highConfidenceBreakdown,
  },
  render: (args) => (
    <div className="flex flex-col gap-4 p-8">
      <p className="text-sm text-muted-foreground max-w-md">
        Press Tab to focus the badge, then hover or keep focus to see the tooltip.
        The tooltip is accessible via keyboard navigation.
      </p>
      <div className="flex items-center gap-4">
        <span className="text-sm text-muted-foreground">Try Tab key:</span>
        <ScoreBreakdownTooltip {...args}>
          <button className="focus:outline-none focus:ring-2 focus:ring-primary rounded">
            <ScoreBadge score={args.breakdown.normalized_score} />
          </button>
        </ScoreBreakdownTooltip>
      </div>
    </div>
  ),
};

/**
 * Multiple tooltips in a row (like in a table)
 */
export const MultipleInRow: Story = {
  render: () => (
    <div className="flex flex-col gap-4 p-8">
      <p className="text-sm text-muted-foreground max-w-md">
        Example of multiple score badges with tooltips in a row, similar to marketplace results.
      </p>
      <div className="flex items-center gap-3">
        <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown}>
          <ScoreBadge score={100} />
        </ScoreBreakdownTooltip>

        <ScoreBreakdownTooltip breakdown={mediumConfidenceBreakdown}>
          <ScoreBadge score={38} />
        </ScoreBreakdownTooltip>

        <ScoreBreakdownTooltip breakdown={withPenaltyBreakdown}>
          <ScoreBadge score={69} />
        </ScoreBreakdownTooltip>

        <ScoreBreakdownTooltip breakdown={lowConfidenceBreakdown}>
          <ScoreBadge score={15} />
        </ScoreBreakdownTooltip>

        <ScoreBreakdownTooltip breakdown={noSignalsBreakdown}>
          <ScoreBadge score={0} />
        </ScoreBreakdownTooltip>
      </div>
    </div>
  ),
};

/**
 * Comparison of all confidence levels
 */
export const AllConfidenceLevels: Story = {
  render: () => (
    <div className="flex flex-col gap-6 p-8">
      <h3 className="text-lg font-semibold">Confidence Score Comparison</h3>

      <div className="grid grid-cols-2 gap-6 max-w-2xl">
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase">
            High Confidence (100)
          </span>
          <div className="flex items-center gap-2">
            <ScoreBreakdownTooltip breakdown={highConfidenceBreakdown}>
              <ScoreBadge score={100} />
            </ScoreBreakdownTooltip>
            <span className="text-sm text-muted-foreground">
              All signals present, no penalty
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase">
            With Penalty (69)
          </span>
          <div className="flex items-center gap-2">
            <ScoreBreakdownTooltip breakdown={withPenaltyBreakdown}>
              <ScoreBadge score={69} />
            </ScoreBreakdownTooltip>
            <span className="text-sm text-muted-foreground">
              Good signals, large depth penalty
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase">
            Medium Confidence (38)
          </span>
          <div className="flex items-center gap-2">
            <ScoreBreakdownTooltip breakdown={mediumConfidenceBreakdown}>
              <ScoreBadge score={38} />
            </ScoreBreakdownTooltip>
            <span className="text-sm text-muted-foreground">
              Partial signals, small penalty
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase">
            Low Confidence (15)
          </span>
          <div className="flex items-center gap-2">
            <ScoreBreakdownTooltip breakdown={lowConfidenceBreakdown}>
              <ScoreBadge score={15} />
            </ScoreBreakdownTooltip>
            <span className="text-sm text-muted-foreground">
              Minimal signals, moderate penalty
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-muted-foreground uppercase">
            No Confidence (0)
          </span>
          <div className="flex items-center gap-2">
            <ScoreBreakdownTooltip breakdown={noSignalsBreakdown}>
              <ScoreBadge score={0} />
            </ScoreBreakdownTooltip>
            <span className="text-sm text-muted-foreground">
              No positive signals, large penalty
            </span>
          </div>
        </div>
      </div>
    </div>
  ),
};
