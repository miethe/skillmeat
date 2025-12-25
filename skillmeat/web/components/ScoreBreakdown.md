# ScoreBreakdown Component

Expandable card component showing trust/quality/match score breakdown with visual progress bars.

## Overview

The ScoreBreakdown component displays a confidence score breakdown into three weighted components:
- **Trust** (25% weight): Source trustworthiness
- **Quality** (25% weight): User ratings + maintenance indicators
- **Match** (50% weight): Semantic relevance to the search query

## Usage

### Basic Example

```tsx
import { ScoreBreakdown } from '@/components/ScoreBreakdown';

function ArtifactCard({ artifact }) {
  return (
    <div className="space-y-4">
      <h2>{artifact.name}</h2>

      <ScoreBreakdown
        confidence={92}
        trust={95}
        quality={87}
        match={92}
      />
    </div>
  );
}
```

### Expanded by Default

```tsx
<ScoreBreakdown
  confidence={92}
  trust={95}
  quality={87}
  match={92}
  defaultExpanded={true}
/>
```

### Custom Weights

```tsx
<ScoreBreakdown
  confidence={88}
  trust={90}
  quality={85}
  match={88}
  weights={{
    trust: 0.3,    // 30%
    quality: 0.2,  // 20%
    match: 0.5,    // 50%
  }}
/>
```

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `confidence` | `number` | Required | Final composite confidence score (0-100) |
| `trust` | `number` | Required | Source trustworthiness score (0-100) |
| `quality` | `number` | Required | User/community ratings + maintenance score (0-100) |
| `match` | `number` | Required | Semantic relevance to query score (0-100) |
| `weights` | `object` | `{ trust: 0.25, quality: 0.25, match: 0.50 }` | Weight configuration for each component |
| `defaultExpanded` | `boolean` | `false` | Whether breakdown is expanded by default |
| `className` | `string` | `undefined` | Additional CSS classes |

## Visual Design

When collapsed, shows only the trigger:
```
▼ Score breakdown
```

When expanded, shows all three components with progress bars:
```
▲ Score breakdown

Trust    95  (25%)
████████████████████░
Source trustworthiness

Quality  87  (25%)
█████████████████░░░
User ratings + maintenance

Match    92  (50%)
██████████████████░░
Relevance to your query

─────────────────────
Formula: (T×0.25) + (Q×0.25) + (M×0.5) = 92%
```

## Accessibility

The component is fully accessible:

- **Keyboard Navigation**: Trigger can be focused and activated with Enter/Space
- **Screen Readers**:
  - Trigger announces "Show/Hide score breakdown"
  - Progress bars have aria-labels with score values
  - Each progress bar has aria-valuemin, aria-valuemax, aria-valuenow
- **Visual Hierarchy**: Clear separation between components
- **Focus Management**: Visible focus ring on trigger button

## Integration Examples

### Artifact Detail View

```tsx
import { ScoreBreakdown } from '@/components/ScoreBreakdown';

export function ArtifactDetailView({ artifact, scores }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{artifact.name}</CardTitle>
        <Badge>Confidence: {scores.confidence}%</Badge>
      </CardHeader>

      <CardContent>
        <ScoreBreakdown
          confidence={scores.confidence}
          trust={scores.trust}
          quality={scores.quality}
          match={scores.match}
        />
      </CardContent>
    </Card>
  );
}
```

### Search Results with Score Context

```tsx
import { ScoreBreakdown } from '@/components/ScoreBreakdown';

export function SearchResultCard({ result }) {
  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-start justify-between">
        <h3>{result.artifact.name}</h3>
        <Badge variant={result.confidence > 80 ? 'success' : 'default'}>
          {result.confidence}%
        </Badge>
      </div>

      <p className="text-sm text-muted-foreground">
        {result.artifact.description}
      </p>

      <ScoreBreakdown
        confidence={result.confidence}
        trust={result.trustScore}
        quality={result.qualityScore}
        match={result.matchScore}
        className="pt-2 border-t"
      />
    </div>
  );
}
```

### Conditional Display (Only Show for Medium Confidence)

```tsx
export function ArtifactCard({ artifact, scores }) {
  // Only show breakdown for scores between 60-85 (users may want explanation)
  const showBreakdown = scores.confidence >= 60 && scores.confidence < 85;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{artifact.name}</CardTitle>
      </CardHeader>

      <CardContent>
        {showBreakdown && (
          <ScoreBreakdown
            confidence={scores.confidence}
            trust={scores.trust}
            quality={scores.quality}
            match={scores.match}
            defaultExpanded={scores.confidence < 70}
          />
        )}
      </CardContent>
    </Card>
  );
}
```

## Testing

The component includes comprehensive tests covering:
- Rendering (collapsed/expanded states)
- Expansion/collapse behavior
- Score component display
- Custom weights
- Formula display
- Accessibility (keyboard navigation, ARIA attributes)
- Edge cases (zero scores, perfect scores, decimal weights)

Run tests:
```bash
pnpm test ScoreBreakdown.test.tsx
```

## Styling

The component uses Tailwind CSS and supports dark mode automatically through CSS variables.

Custom styling via className:
```tsx
<ScoreBreakdown
  {...scores}
  className="mt-4 border-t pt-4"
/>
```

## Related Components

- `Progress` - Base progress bar component (Radix UI)
- `Collapsible` - Base collapsible component (Radix UI)
- Badge - For displaying confidence level
- Card - For containing score breakdown in larger layouts

## Future Enhancements

Potential improvements for future phases:
- Color-coded progress bars based on score thresholds
- Tooltips explaining each component
- Animation on expand/collapse
- Export breakdown as image/screenshot
- Historical score comparison view
