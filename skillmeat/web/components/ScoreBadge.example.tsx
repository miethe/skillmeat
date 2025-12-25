/**
 * ScoreBadge Usage Examples
 *
 * Demonstrates different ways to use the ScoreBadge component
 * with various confidence scores and styling options.
 */

import { ScoreBadge, ScoreBadgeSkeleton } from './ScoreBadge';

/**
 * Basic usage with different confidence levels
 */
export function BasicExample() {
  return (
    <div className="space-y-4 p-4">
      <h3 className="text-lg font-semibold">Confidence Score Examples</h3>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="w-32">High (85%):</span>
          <ScoreBadge confidence={85} />
        </div>

        <div className="flex items-center gap-2">
          <span className="w-32">Medium (60%):</span>
          <ScoreBadge confidence={60} />
        </div>

        <div className="flex items-center gap-2">
          <span className="w-32">Low (30%):</span>
          <ScoreBadge confidence={30} />
        </div>
      </div>
    </div>
  );
}

/**
 * Size variants
 */
export function SizeExample() {
  return (
    <div className="space-y-4 p-4">
      <h3 className="text-lg font-semibold">Size Variants</h3>

      <div className="flex items-center gap-4">
        <div className="flex flex-col items-center gap-2">
          <span className="text-xs text-muted-foreground">Small</span>
          <ScoreBadge confidence={87} size="sm" />
        </div>

        <div className="flex flex-col items-center gap-2">
          <span className="text-xs text-muted-foreground">Medium</span>
          <ScoreBadge confidence={87} size="md" />
        </div>

        <div className="flex flex-col items-center gap-2">
          <span className="text-xs text-muted-foreground">Large</span>
          <ScoreBadge confidence={87} size="lg" />
        </div>
      </div>
    </div>
  );
}

/**
 * In artifact card (real-world usage)
 */
export function ArtifactCardExample() {
  const mockArtifact = {
    id: 'skill:pdf-processor',
    name: 'pdf-processor',
    type: 'skill' as const,
    score: {
      confidence: 87,
      trustScore: 90,
      qualityScore: 85,
    },
  };

  return (
    <div className="space-y-4 p-4">
      <h3 className="text-lg font-semibold">In Artifact Card</h3>

      <div className="rounded-lg border p-4">
        <div className="flex items-start justify-between">
          <div>
            <h4 className="font-semibold">{mockArtifact.name}</h4>
            <p className="text-sm text-muted-foreground">{mockArtifact.type}</p>
          </div>

          <div className="flex items-center gap-2">
            {mockArtifact.score && (
              <ScoreBadge confidence={mockArtifact.score.confidence} size="sm" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Loading state
 */
export function LoadingExample() {
  return (
    <div className="space-y-4 p-4">
      <h3 className="text-lg font-semibold">Loading State</h3>

      <div className="rounded-lg border p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="h-4 w-32 animate-pulse rounded bg-muted" />
            <div className="h-3 w-24 animate-pulse rounded bg-muted" />
          </div>

          <div className="flex items-center gap-2">
            <ScoreBadgeSkeleton size="sm" />
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Boundary cases
 */
export function BoundaryExample() {
  return (
    <div className="space-y-4 p-4">
      <h3 className="text-lg font-semibold">Boundary Cases</h3>

      <div className="space-y-2">
        <div className="flex items-center gap-2">
          <span className="w-32">Exactly 70%:</span>
          <ScoreBadge confidence={70} />
        </div>

        <div className="flex items-center gap-2">
          <span className="w-32">Exactly 71%:</span>
          <ScoreBadge confidence={71} />
        </div>

        <div className="flex items-center gap-2">
          <span className="w-32">Exactly 50%:</span>
          <ScoreBadge confidence={50} />
        </div>

        <div className="flex items-center gap-2">
          <span className="w-32">Exactly 49%:</span>
          <ScoreBadge confidence={49} />
        </div>

        <div className="flex items-center gap-2">
          <span className="w-32">Minimum (0%):</span>
          <ScoreBadge confidence={0} />
        </div>

        <div className="flex items-center gap-2">
          <span className="w-32">Maximum (100%):</span>
          <ScoreBadge confidence={100} />
        </div>
      </div>
    </div>
  );
}

/**
 * All examples in one page
 */
export default function ScoreBadgeExamples() {
  return (
    <div className="container mx-auto space-y-8 py-8">
      <h1 className="text-2xl font-bold">ScoreBadge Component Examples</h1>

      <BasicExample />
      <SizeExample />
      <ArtifactCardExample />
      <LoadingExample />
      <BoundaryExample />
    </div>
  );
}
