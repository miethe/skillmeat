# TrustBadges Integration Guide

Guide for integrating TrustBadges component into existing artifact and entity cards.

## Component Location

- **Component**: `/components/TrustBadges.tsx`
- **Tests**: `/__tests__/components/TrustBadges.test.tsx`
- **Examples**: `/components/TrustBadges.example.tsx`

## Integration with UnifiedCard

To add trust badges to the UnifiedCard component:

### Step 1: Import the component and helper

```typescript
import { TrustBadges, getTrustLevelFromSource } from '@/components/TrustBadges';
```

### Step 2: Determine trust level from source

```typescript
// Inside the UnifiedCard component function
const trustLevel = data.source ? getTrustLevelFromSource(data.source) : 'community';
```

### Step 3: Add badge to the card header

Add the TrustBadges component alongside existing status badges in the header section:

```tsx
{/* Status badge and actions - Around line 356 in unified-card.tsx */}
<div className="flex flex-shrink-0 items-center gap-2">
  {/* Existing status badge */}
  {data.status && (
    <Badge className={cn('flex-shrink-0', statusColors[data.status])} variant="outline">
      {statusLabels[data.status] || data.status}
    </Badge>
  )}

  {/* NEW: Add trust badge */}
  {data.source && (
    <TrustBadges
      trustLevel={trustLevel}
      source={data.source}
      className="flex-shrink-0"
    />
  )}

  {/* Existing entity actions */}
  {isEntity(item) && (
    <EntityActions
      entity={item}
      onEdit={onEdit}
      // ...
    />
  )}
</div>
```

### Complete Integration Example

```typescript
// In unified-card.tsx, around line 197
export const UnifiedCard = React.memo(
  function UnifiedCard({
    item,
    selected = false,
    // ... other props
  }: UnifiedCardProps) {
    const queryClient = useQueryClient();
    const data = normalizeCardData(item);
    const config = getEntityTypeConfig(data.type as EntityType);

    // NEW: Determine trust level from source
    const trustLevel = data.source ? getTrustLevelFromSource(data.source) : 'community';

    // ... existing component logic

    return (
      <Card>
        {/* Header with icon and status badge */}
        <div className="p-4 pb-3">
          <div className="flex items-start justify-between gap-2">
            {/* ... existing header content */}

            {/* Status badge and actions */}
            <div className="flex flex-shrink-0 items-center gap-2">
              {data.status && (
                <Badge className={cn('flex-shrink-0', statusColors[data.status])} variant="outline">
                  {statusLabels[data.status] || data.status}
                </Badge>
              )}

              {/* NEW: Trust badge */}
              {data.source && (
                <TrustBadges
                  trustLevel={trustLevel}
                  source={data.source}
                  className="flex-shrink-0"
                />
              )}

              {isEntity(item) && (
                <EntityActions
                  entity={item}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onDeploy={onDeploy}
                  onSync={onSync}
                  onViewDiff={onViewDiff}
                  onRollback={onRollback}
                />
              )}
            </div>
          </div>
        </div>

        {/* ... rest of card content */}
      </Card>
    );
  }
);
```

## Alternative: Add to metadata row

If you prefer to show trust badges in the metadata row instead of the header:

```tsx
{/* Metadata row - Around line 385 */}
<div className="flex items-center gap-4 text-xs text-muted-foreground">
  {/* Trust badge */}
  {data.source && (
    <TrustBadges
      trustLevel={getTrustLevelFromSource(data.source)}
      source={data.source}
    />
  )}

  {/* Existing metadata items */}
  {data.version && (
    <div className="flex items-center gap-1" title="Version">
      <LucideIcons.Package className="h-3 w-3" />
      <span>{data.version}</span>
    </div>
  )}
  {/* ... */}
</div>
```

## Integration with Marketplace Components

TrustBadges can also be used alongside the existing marketplace TrustBadge component:

```tsx
// In marketplace source cards or listings
import { TrustBadges as ArtifactTrustBadges } from '@/components/TrustBadges';

// For artifact trust levels (official/verified/community)
<ArtifactTrustBadges trustLevel="official" source={artifact.source} />

// For source trust levels (untrusted/basic/verified/official)
<TrustBadge level={source.trust_level} />
```

## Trust Level Determination Logic

The `getTrustLevelFromSource()` helper uses these rules:

### Official Sources
- Contains `anthropic/` or `anthropics/` (case insensitive)
- Starts with `claude-` (case insensitive)
- Examples:
  - `anthropics/skills/canvas` → official
  - `github.com/anthropic/skills` → official
  - `claude-marketplace/skill` → official

### Verified Sources
- Starts with `verified/` (case insensitive)
- Starts with `trusted-` (case insensitive)
- Examples:
  - `verified/community-skills` → verified
  - `trusted-user/repo` → verified

### Community Sources
- All other sources default to community
- Examples:
  - `user/repo/skill` → community
  - `custom-source` → community

## Type Safety

The component is fully typed:

```typescript
import type { TrustLevel } from '@/components/TrustBadges';

// Trust level type
type TrustLevel = 'official' | 'verified' | 'community';

// Component props
interface TrustBadgesProps {
  trustLevel: TrustLevel;
  source?: string;
  className?: string;
}

// Helper function
function getTrustLevelFromSource(source: string): TrustLevel;
```

## Accessibility

The component includes:
- `aria-label` on badges for screen readers
- Keyboard-focusable tooltips
- High contrast colors for readability
- Dark mode support

## Testing

Run the component tests:

```bash
pnpm test TrustBadges.test.tsx
```

All 21 tests should pass, covering:
- Badge rendering for all trust levels
- Tooltip display and content
- Source detection logic
- Edge cases and accessibility

## Visual Examples

See the examples page for visual demonstrations:

```bash
# Import examples in your page
import { TrustBadgesExamplesPage } from '@/components/TrustBadges.example';

// Or individual examples
import {
  ExampleSimple,
  ExampleWithSource,
  ExampleAutoDetect,
  ArtifactCardExample
} from '@/components/TrustBadges.example';
```
