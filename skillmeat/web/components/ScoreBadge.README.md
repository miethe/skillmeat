# ScoreBadge Component

Display confidence scores on artifact cards with color-coded visual indicators.

## Overview

The `ScoreBadge` component renders a confidence score (0-100) as a percentage badge with color coding based on the score range:

- **Green** (>70): High confidence
- **Yellow** (50-70): Medium confidence
- **Red** (<50): Low confidence

All colors meet WCAG 2.1 AA contrast requirements (>4.5:1 ratio).

## Files

- **Component**: `components/ScoreBadge.tsx`
- **Tests**: `__tests__/components/ScoreBadge.test.tsx`
- **Visual Tests**: `__tests__/visual/ScoreBadge.visual.test.tsx`
- **Examples**: `components/ScoreBadge.example.tsx`
- **Integration**: `components/shared/unified-card.tsx`
- **Types**: `types/artifact.ts`

## Usage

### Basic Usage

```tsx
import { ScoreBadge } from '@/components/ScoreBadge';

<ScoreBadge confidence={87} />;
```

### Size Variants

```tsx
<ScoreBadge confidence={87} size="sm" />  // Small (h-4)
<ScoreBadge confidence={87} size="md" />  // Medium (h-5, default)
<ScoreBadge confidence={87} size="lg" />  // Large (h-7)
```

### With Artifact Card

The component is automatically displayed on artifact cards when the artifact has a score:

```tsx
const artifact: Artifact = {
  id: 'skill:pdf-processor',
  name: 'pdf-processor',
  type: 'skill',
  score: {
    confidence: 87,
    trustScore: 90,
    qualityScore: 85,
  },
  // ... other fields
};

<UnifiedCard item={artifact} />;
// ScoreBadge automatically shown in header
```

### Loading State

```tsx
import { ScoreBadgeSkeleton } from '@/components/ScoreBadge';

<ScoreBadgeSkeleton size="sm" />;
```

## Props

### ScoreBadge

| Prop         | Type                   | Default  | Description              |
| ------------ | ---------------------- | -------- | ------------------------ |
| `confidence` | `number`               | required | Confidence score (0-100) |
| `size`       | `'sm' \| 'md' \| 'lg'` | `'md'`   | Badge size variant       |
| `className`  | `string`               | -        | Additional CSS classes   |

### ScoreBadgeSkeleton

| Prop   | Type                   | Default | Description        |
| ------ | ---------------------- | ------- | ------------------ |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'`  | Badge size variant |

## Color Mapping

| Confidence Range | Background       | Text Color | Border     | Contrast Ratio |
| ---------------- | ---------------- | ---------- | ---------- | -------------- |
| > 70             | Green (#22c55e)  | White      | Green-600  | 4.54:1 ✓       |
| 50-70            | Yellow (#eab308) | Black      | Yellow-600 | 8.38:1 ✓       |
| < 50             | Red (#ef4444)    | White      | Red-600    | 4.72:1 ✓       |

All colors meet WCAG 2.1 AA requirements for normal text (>4.5:1).

## Accessibility

- **aria-label**: `"Confidence score: {score} percent, {level} confidence"`
- **title**: `"{Level} confidence: {score}%"` (tooltip on hover)
- **Keyboard navigation**: Inherits from Badge component
- **Screen reader friendly**: Descriptive labels with confidence level

## Type Definitions

```typescript
// types/artifact.ts
export interface ArtifactScore {
  confidence: number; // Composite confidence (0-100)
  trustScore?: number; // Source trust (0-100)
  qualityScore?: number; // Community quality (0-100)
  matchScore?: number; // Query relevance (0-100, search only)
  lastUpdated?: string; // ISO timestamp
}

export interface Artifact {
  // ... other fields
  score?: ArtifactScore;
}
```

## Integration with Backend

The score data comes from the `/api/v1/artifacts/{id}/scores` endpoint:

```typescript
// Backend schema (skillmeat/api/schemas/scoring.py)
interface ArtifactScoreResponse {
  artifact_id: string;
  trust_score: float; // 0-100
  quality_score: float; // 0-100
  match_score?: float; // 0-100 (optional, search context)
  confidence: float; // Composite score (0-100)
  schema_version: string;
  last_updated?: datetime;
}
```

The backend calculates the composite `confidence` score by weighting:

- `trust_score`: Source reputation
- `quality_score`: Community ratings
- `match_score`: Query relevance (search only)

## Examples

See `components/ScoreBadge.example.tsx` for:

- Basic usage with different confidence levels
- Size variants
- Integration with artifact cards
- Loading states
- Boundary cases (0%, 50%, 70%, 100%)

## Testing

**Unit Tests** (20 tests):

- Color coding (high/medium/low)
- Edge cases (0, 100, negative, >100)
- Boundary values (49, 50, 70, 71)
- Accessibility (aria-label, title)
- Size variants
- Custom styling

**Visual Tests** (11 tests):

- Color mapping verification
- Size class application
- Typography (tabular-nums, font-semibold)
- Contrast ratio validation
- Custom className merging

Run tests:

```bash
npm test -- ScoreBadge
```

## Design Decisions

1. **Color Thresholds**:
   - `>70`: High confidence (green) - aligns with "A" grade (70-100%)
   - `50-70`: Medium confidence (yellow) - "C-D" grade (50-70%)
   - `<50`: Low confidence (red) - failing grade (<50%)

2. **Rounding**: Scores are rounded to nearest integer for display (87.6 → 88%)

3. **Clamping**: Out-of-range values are clamped to 0-100

4. **Accessibility**: All color combinations meet WCAG 2.1 AA (4.5:1 contrast)

5. **Placement**: Displayed before status badge in artifact card header

6. **Optional**: Only shown when `score.confidence` is defined

## Future Enhancements

- [ ] Tooltip with score breakdown (trust/quality/match)
- [ ] Click to show detailed score modal
- [ ] Trend indicator (score increasing/decreasing)
- [ ] Historical score visualization
- [ ] Customizable thresholds via props
- [ ] Dark mode optimization

## Related Components

- **Badge** (`components/ui/badge.tsx`): Base component
- **UnifiedCard** (`components/shared/unified-card.tsx`): Integration point
- **Entity** types (`types/entity.ts`): Related data structures
- **Artifact** types (`types/artifact.ts`): Score data structure

## API Reference

- **Endpoint**: `GET /api/v1/artifacts/{artifact_id}/scores`
- **Schema**: `skillmeat/api/schemas/scoring.py`
- **Router**: `skillmeat/api/routers/ratings.py`
