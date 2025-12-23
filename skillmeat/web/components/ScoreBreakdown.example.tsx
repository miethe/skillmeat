/**
 * Example integration of ScoreBreakdown component with artifact views
 *
 * This file demonstrates how to integrate the ScoreBreakdown component
 * into various artifact display contexts.
 */

import { ScoreBreakdown } from '@/components/ScoreBreakdown';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

/**
 * Example 1: Integration with Artifact Detail View
 *
 * Shows how to add score breakdown to an artifact detail page.
 * Scores would come from the confidence scoring system (Phase 4).
 */
export function ArtifactDetailWithScores() {
  // In real implementation, these would come from:
  // - API response with confidence scores
  // - Local calculation based on trust/quality/match algorithms
  const artifactData = {
    name: 'canvas-design',
    type: 'skill',
    description: 'Design and layout artifacts using canvas',
    version: '2.1.0',
    source: 'anthropics/skills/canvas-design',
  };

  const confidenceScores = {
    confidence: 92, // Composite score
    trust: 95, // Source trustworthiness (official Anthropic repo)
    quality: 87, // User ratings + maintenance indicators
    match: 92, // Semantic relevance to current query
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <CardTitle>{artifactData.name}</CardTitle>
            <p className="text-sm text-muted-foreground">{artifactData.description}</p>
          </div>
          <Badge
            variant={confidenceScores.confidence > 80 ? 'default' : 'secondary'}
            className="ml-4"
          >
            {confidenceScores.confidence}% confidence
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">Type:</span> {artifactData.type}
          </div>
          <div>
            <span className="text-muted-foreground">Version:</span> {artifactData.version}
          </div>
          <div className="col-span-2">
            <span className="text-muted-foreground">Source:</span> {artifactData.source}
          </div>
        </div>

        {/* Score Breakdown Integration */}
        <div className="border-t pt-4">
          <ScoreBreakdown
            confidence={confidenceScores.confidence}
            trust={confidenceScores.trust}
            quality={confidenceScores.quality}
            match={confidenceScores.match}
          />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Example 2: Integration with Search Results
 *
 * Shows score breakdown in search/discovery context where match score
 * is particularly relevant.
 */
export function SearchResultCardWithScores({
  artifact,
  query,
}: {
  artifact: {
    id: string;
    name: string;
    description: string;
    type: string;
  };
  query: string;
}) {
  // In real implementation, these scores would be calculated by:
  // - Match: Semantic similarity to search query
  // - Trust: Source repository trust score
  // - Quality: Community ratings + maintenance metrics
  const scores = {
    confidence: 88,
    trust: 90,
    quality: 85,
    match: 88, // High because it matched the query well
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="pt-6 space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold">{artifact.name}</h3>
            <p className="text-sm text-muted-foreground mt-1">{artifact.description}</p>
          </div>
          <Badge variant={scores.confidence > 85 ? 'default' : 'secondary'}>
            {scores.confidence}%
          </Badge>
        </div>

        <div className="text-xs text-muted-foreground">
          <span className="font-medium">Matched query:</span> &quot;{query}&quot;
        </div>

        {/* Auto-expand for medium confidence scores (user may want explanation) */}
        <ScoreBreakdown
          confidence={scores.confidence}
          trust={scores.trust}
          quality={scores.quality}
          match={scores.match}
          defaultExpanded={scores.confidence >= 70 && scores.confidence < 90}
          className="border-t pt-3"
        />
      </CardContent>
    </Card>
  );
}

/**
 * Example 3: Compact Grid View with Score Indicator
 *
 * Shows minimal score display in grid/list views, with expandable details.
 */
export function ArtifactGridItemWithScore({
  artifact,
}: {
  artifact: {
    id: string;
    name: string;
    type: string;
  };
}) {
  const scores = {
    confidence: 76,
    trust: 85,
    quality: 70,
    match: 75,
  };

  return (
    <Card className="h-full">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base">{artifact.name}</CardTitle>
          <Badge variant="outline" className="text-xs">
            {scores.confidence}%
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="text-xs text-muted-foreground mb-3">{artifact.type}</div>

        {/* Minimal score breakdown for space-constrained layouts */}
        <ScoreBreakdown
          confidence={scores.confidence}
          trust={scores.trust}
          quality={scores.quality}
          match={scores.match}
          className="text-xs"
        />
      </CardContent>
    </Card>
  );
}

/**
 * Example 4: Comparison View with Custom Weights
 *
 * Shows how to use custom weights when comparing artifacts with
 * different scoring priorities.
 */
export function ArtifactComparisonWithScores() {
  const artifact1 = {
    name: 'production-skill',
    scores: { confidence: 95, trust: 100, quality: 90, match: 95 },
  };

  const artifact2 = {
    name: 'experimental-skill',
    scores: { confidence: 75, trust: 60, quality: 85, match: 80 },
  };

  // Emphasize trust for production scenarios
  const productionWeights = {
    trust: 0.5, // 50% weight on trust
    quality: 0.3, // 30% weight on quality
    match: 0.2, // 20% weight on match
  };

  return (
    <div className="grid grid-cols-2 gap-4">
      <Card>
        <CardHeader>
          <CardTitle>{artifact1.name}</CardTitle>
          <Badge>Production Ready</Badge>
        </CardHeader>
        <CardContent>
          <ScoreBreakdown
            confidence={artifact1.scores.confidence}
            trust={artifact1.scores.trust}
            quality={artifact1.scores.quality}
            match={artifact1.scores.match}
            weights={productionWeights}
            defaultExpanded
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{artifact2.name}</CardTitle>
          <Badge variant="secondary">Experimental</Badge>
        </CardHeader>
        <CardContent>
          <ScoreBreakdown
            confidence={artifact2.scores.confidence}
            trust={artifact2.scores.trust}
            quality={artifact2.scores.quality}
            match={artifact2.scores.match}
            weights={productionWeights}
            defaultExpanded
          />
        </CardContent>
      </Card>
    </div>
  );
}

/**
 * Example 5: Conditional Display Based on Confidence Threshold
 *
 * Only show breakdown for artifacts with ambiguous confidence scores.
 */
export function ArtifactCardWithConditionalBreakdown({
  artifact,
  scores,
}: {
  artifact: { name: string; description: string };
  scores: { confidence: number; trust: number; quality: number; match: number };
}) {
  // Only show breakdown if confidence is in "uncertain" range
  const showBreakdown = scores.confidence >= 50 && scores.confidence < 85;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{artifact.name}</CardTitle>
        <p className="text-sm text-muted-foreground">{artifact.description}</p>
      </CardHeader>

      <CardContent>
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium">Confidence</span>
          <Badge
            variant={
              scores.confidence >= 85
                ? 'default'
                : scores.confidence >= 70
                  ? 'secondary'
                  : 'outline'
            }
          >
            {scores.confidence}%
          </Badge>
        </div>

        {showBreakdown && (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              This artifact has moderate confidence. See breakdown below:
            </p>
            <ScoreBreakdown
              confidence={scores.confidence}
              trust={scores.trust}
              quality={scores.quality}
              match={scores.match}
              defaultExpanded={scores.confidence < 70}
            />
          </div>
        )}

        {scores.confidence >= 85 && (
          <p className="text-xs text-muted-foreground">
            ✓ High confidence - recommended for use
          </p>
        )}

        {scores.confidence < 50 && (
          <div className="space-y-2">
            <p className="text-xs text-yellow-600 dark:text-yellow-400">
              ⚠ Low confidence - review carefully before using
            </p>
            <ScoreBreakdown
              confidence={scores.confidence}
              trust={scores.trust}
              quality={scores.quality}
              match={scores.match}
              defaultExpanded
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
