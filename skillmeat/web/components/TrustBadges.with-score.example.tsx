/**
 * TrustBadges + ScoreBadge Integration Example
 *
 * Shows how TrustBadges and ScoreBadge can be used together on artifact cards.
 */

'use client';

import { TrustBadges, getTrustLevelFromSource } from './TrustBadges';
import { ScoreBadge } from './ScoreBadge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

/**
 * Example artifact with both trust and confidence data
 */
interface ExampleArtifact {
  id: string;
  name: string;
  description: string;
  source: string;
  type: string;
  version?: string;
  confidenceScore?: number; // 0-100
}

/**
 * Example 1: Trust and Score badges side by side
 */
export function ArtifactCardWithBothBadges({ artifact }: { artifact: ExampleArtifact }) {
  const trustLevel = getTrustLevelFromSource(artifact.source);

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle>{artifact.name}</CardTitle>
          {/* Multiple badges: type, trust, and score */}
          <div className="flex flex-shrink-0 flex-wrap gap-1">
            <Badge variant="secondary">{artifact.type}</Badge>
            <TrustBadges trustLevel={trustLevel} source={artifact.source} />
            {artifact.confidenceScore !== undefined && (
              <ScoreBadge confidence={artifact.confidenceScore} size="sm" />
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="mb-2 text-sm text-muted-foreground">{artifact.description}</p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {artifact.version && <span>v{artifact.version}</span>}
          <span>{artifact.source}</span>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Example 2: Trust and Score in different locations
 */
export function ArtifactCardSplitBadges({ artifact }: { artifact: ExampleArtifact }) {
  const trustLevel = getTrustLevelFromSource(artifact.source);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          {/* Name and type on left */}
          <div className="flex items-center gap-2">
            <CardTitle>{artifact.name}</CardTitle>
            <Badge variant="secondary">{artifact.type}</Badge>
          </div>
          {/* Trust badge on right */}
          <TrustBadges trustLevel={trustLevel} source={artifact.source} />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{artifact.description}</p>
        {/* Score badge in content area */}
        <div className="flex items-center gap-2">
          {artifact.confidenceScore !== undefined && (
            <>
              <span className="text-xs text-muted-foreground">Confidence:</span>
              <ScoreBadge confidence={artifact.confidenceScore} size="sm" />
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Example 3: Conditional badges based on data availability
 */
export function ArtifactCardConditional({ artifact }: { artifact: ExampleArtifact }) {
  const trustLevel = getTrustLevelFromSource(artifact.source);
  const hasScore = artifact.confidenceScore !== undefined;
  const hasSource = Boolean(artifact.source);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle>{artifact.name}</CardTitle>
          <div className="flex flex-shrink-0 gap-1">
            {/* Always show type */}
            <Badge variant="secondary">{artifact.type}</Badge>

            {/* Show trust badge only if source exists */}
            {hasSource && <TrustBadges trustLevel={trustLevel} source={artifact.source} />}

            {/* Show score badge only if score exists */}
            {hasScore && <ScoreBadge confidence={artifact.confidenceScore!} size="sm" />}
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

/**
 * Example 4: Full artifact card with all badges and metadata
 */
export function FullArtifactCard({ artifact }: { artifact: ExampleArtifact }) {
  const trustLevel = getTrustLevelFromSource(artifact.source);

  return (
    <Card className="transition-shadow hover:shadow-lg">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="space-y-1">
            <CardTitle>{artifact.name}</CardTitle>
            {artifact.version && (
              <p className="text-xs text-muted-foreground">Version {artifact.version}</p>
            )}
          </div>
          <div className="flex flex-shrink-0 gap-1">
            <TrustBadges trustLevel={trustLevel} source={artifact.source} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Description */}
        <p className="text-sm text-muted-foreground">{artifact.description}</p>

        {/* Metadata row with badges */}
        <div className="flex items-center gap-4 text-xs">
          <Badge variant="secondary">{artifact.type}</Badge>
          {artifact.confidenceScore !== undefined && (
            <div className="flex items-center gap-1">
              <span className="text-muted-foreground">Score:</span>
              <ScoreBadge confidence={artifact.confidenceScore} size="sm" />
            </div>
          )}
        </div>

        {/* Source info */}
        <div className="text-xs text-muted-foreground">
          <span>Source: {artifact.source}</span>
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Example usage page showing different layouts
 */
export function TrustAndScoreBadgesPage() {
  const artifacts: ExampleArtifact[] = [
    {
      id: '1',
      name: 'Canvas Design',
      description: 'Official canvas design skill from Anthropic',
      source: 'anthropics/skills/canvas-design',
      type: 'skill',
      version: '2.1.0',
      confidenceScore: 95,
    },
    {
      id: '2',
      name: 'Code Review',
      description: 'Community verified code review skill',
      source: 'verified/community/code-review',
      type: 'skill',
      version: '1.0.0',
      confidenceScore: 78,
    },
    {
      id: '3',
      name: 'Custom Helper',
      description: 'User-contributed helper skill',
      source: 'user/repo/custom-helper',
      type: 'skill',
      version: '0.5.0',
      confidenceScore: 45,
    },
    {
      id: '4',
      name: 'Data Parser',
      description: 'No confidence score available',
      source: 'user/repo/data-parser',
      type: 'command',
      version: '1.2.0',
    },
  ];

  return (
    <div className="container mx-auto space-y-8 p-6">
      <h1 className="text-3xl font-bold">TrustBadges + ScoreBadge Examples</h1>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Badges Together</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {artifacts.map((artifact) => (
            <ArtifactCardWithBothBadges key={artifact.id} artifact={artifact} />
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Badges Split</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {artifacts.map((artifact) => (
            <ArtifactCardSplitBadges key={artifact.id} artifact={artifact} />
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Conditional Badges</h2>
        <div className="grid gap-4 md:grid-cols-2">
          {artifacts.map((artifact) => (
            <ArtifactCardConditional key={artifact.id} artifact={artifact} />
          ))}
        </div>
      </div>

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Full Card Layout</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {artifacts.map((artifact) => (
            <FullArtifactCard key={artifact.id} artifact={artifact} />
          ))}
        </div>
      </div>
    </div>
  );
}

/**
 * Visual reference for badge combinations
 */
export function BadgeCombinationsGuide() {
  return (
    <div className="space-y-6 rounded-lg bg-muted p-6">
      <h3 className="text-lg font-semibold">Badge Combinations Guide</h3>

      <div className="space-y-4">
        <div>
          <h4 className="mb-2 text-sm font-medium">Official Artifact (High Confidence)</h4>
          <div className="flex gap-1">
            <TrustBadges trustLevel="official" source="anthropics/skills/canvas" />
            <ScoreBadge confidence={95} size="sm" />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Best combination: Official source + high confidence = most trustworthy
          </p>
        </div>

        <div>
          <h4 className="mb-2 text-sm font-medium">Verified Artifact (Medium Confidence)</h4>
          <div className="flex gap-1">
            <TrustBadges trustLevel="verified" source="verified/community/skill" />
            <ScoreBadge confidence={65} size="sm" />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Good combination: Verified source + medium confidence = reliable
          </p>
        </div>

        <div>
          <h4 className="mb-2 text-sm font-medium">Community Artifact (Low Confidence)</h4>
          <div className="flex gap-1">
            <TrustBadges trustLevel="community" source="user/repo/skill" />
            <ScoreBadge confidence={45} size="sm" />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Caution: Community source + low confidence = use with care
          </p>
        </div>

        <div>
          <h4 className="mb-2 text-sm font-medium">Official Artifact (No Score)</h4>
          <div className="flex gap-1">
            <TrustBadges trustLevel="official" source="anthropics/skills/new" />
            <Badge variant="outline" className="text-xs">
              Not scored
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Official source but no confidence score available yet
          </p>
        </div>
      </div>
    </div>
  );
}
