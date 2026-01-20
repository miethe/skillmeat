/**
 * TrustBadges - Usage Examples
 *
 * Examples showing how to use the TrustBadges component with artifact cards
 */

'use client';

import { TrustBadges, getTrustLevelFromSource } from './TrustBadges';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

/**
 * Example 1: Simple usage with explicit trust level
 */
export function ExampleSimple() {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Simple Usage</h3>
      <div className="flex gap-2">
        <TrustBadges trustLevel="official" />
        <TrustBadges trustLevel="verified" />
        <TrustBadges trustLevel="community" />
      </div>
    </div>
  );
}

/**
 * Example 2: Usage with source information in tooltip
 */
export function ExampleWithSource() {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">With Source Info</h3>
      <div className="flex gap-2">
        <TrustBadges trustLevel="official" source="anthropics/skills/canvas-design" />
        <TrustBadges trustLevel="verified" source="verified/community-skills" />
        <TrustBadges trustLevel="community" source="user/my-custom-skills" />
      </div>
    </div>
  );
}

/**
 * Example 3: Auto-detect trust level from source
 */
export function ExampleAutoDetect() {
  const sources = [
    'anthropics/skills/canvas-design',
    'verified/trusted-repo/skill',
    'user/repo/custom-skill',
    'claude-marketplace/official-skill',
  ];

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Auto-detect from Source</h3>
      <div className="space-y-2">
        {sources.map((source) => {
          const trustLevel = getTrustLevelFromSource(source);
          return (
            <div key={source} className="flex items-center gap-2">
              <code className="rounded bg-muted px-2 py-1 text-sm">{source}</code>
              <span>→</span>
              <TrustBadges trustLevel={trustLevel} source={source} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

/**
 * Example 4: Integration with artifact card
 */
interface ArtifactCardExampleProps {
  artifact: {
    id: string;
    name: string;
    description: string;
    source: string;
    type: string;
    version?: string;
  };
}

export function ArtifactCardExample({ artifact }: ArtifactCardExampleProps) {
  // Auto-detect trust level from source
  const trustLevel = getTrustLevelFromSource(artifact.source);

  return (
    <Card className="border-l-4 border-l-blue-500">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle>{artifact.name}</CardTitle>
          {/* Trust badge alongside other badges */}
          <div className="flex flex-shrink-0 gap-1">
            <Badge variant="secondary">{artifact.type}</Badge>
            <TrustBadges trustLevel={trustLevel} source={artifact.source} />
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
 * Example 5: Multiple trust badges on same card
 */
export function ExampleMultipleBadges() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <CardTitle>Canvas Design Skill</CardTitle>
          {/* Multiple badges together */}
          <div className="flex flex-wrap gap-1">
            <TrustBadges trustLevel="official" source="anthropics/skills/canvas" />
            <Badge variant="secondary">skill</Badge>
            <Badge variant="outline">v2.1.0</Badge>
          </div>
        </div>
      </CardHeader>
    </Card>
  );
}

/**
 * Example usage in a page component
 */
export function TrustBadgesExamplesPage() {
  const sampleArtifact = {
    id: '1',
    name: 'Canvas Design',
    description: 'Official canvas design skill from Anthropic',
    source: 'anthropics/skills/canvas-design',
    type: 'skill',
    version: '2.1.0',
  };

  return (
    <div className="container mx-auto space-y-8 p-6">
      <h1 className="text-3xl font-bold">TrustBadges Examples</h1>

      <ExampleSimple />
      <ExampleWithSource />
      <ExampleAutoDetect />
      <ExampleMultipleBadges />

      <div className="space-y-4">
        <h3 className="text-lg font-semibold">Artifact Card Integration</h3>
        <ArtifactCardExample artifact={sampleArtifact} />
      </div>
    </div>
  );
}
