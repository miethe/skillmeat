# TrustBadges Component

Display trust badges (Official, Verified, Community) based on artifact source configuration.

## Overview

The TrustBadges component provides visual trust indicators for artifacts, helping users quickly identify the source and reliability of artifacts in the SkillMeat collection.

## Features

- ✓ Three trust levels: Official, Verified, Community
- ✓ Visual badges with icons and tooltips
- ✓ Auto-detection of trust level from source string
- ✓ Keyboard accessible (focusable tooltips)
- ✓ Dark mode support
- ✓ TypeScript type safety
- ✓ Fully tested (21 tests, 100% pass rate)

## Files

```
components/
├── TrustBadges.tsx              # Main component
├── TrustBadges.example.tsx      # Usage examples
└── TrustBadges.integration.md   # Integration guide

__tests__/components/
└── TrustBadges.test.tsx         # Component tests
```

## Quick Start

### Basic Usage

```tsx
import { TrustBadges } from '@/components/TrustBadges';

// Simple usage
<TrustBadges trustLevel="official" />
<TrustBadges trustLevel="verified" />
<TrustBadges trustLevel="community" />

// With source info in tooltip
<TrustBadges
  trustLevel="official"
  source="anthropics/skills/canvas-design"
/>
```

### Auto-detect from Source

```tsx
import { TrustBadges, getTrustLevelFromSource } from '@/components/TrustBadges';

const source = 'anthropics/skills/canvas-design';
const trustLevel = getTrustLevelFromSource(source);

<TrustBadges trustLevel={trustLevel} source={source} />
```

## Badge Types

### Official (Blue)
- **Icon**: ShieldCheck ✓
- **Color**: Blue border/background
- **Tooltip**: "Official artifact from trusted source"
- **Sources**: Contains `anthropic/`, `anthropics/`, or starts with `claude-`
- **Example**: `anthropics/skills/canvas-design`

### Verified (Green)
- **Icon**: ShieldCheck ✓
- **Color**: Green border/background
- **Tooltip**: "Community verified artifact"
- **Sources**: Starts with `verified/` or `trusted-`
- **Example**: `verified/community-skills`

### Community (Gray)
- **Icon**: Shield
- **Color**: Gray border/background
- **Tooltip**: "Community contributed artifact"
- **Sources**: All other sources (default)
- **Example**: `user/repo/custom-skill`

## API

### TrustBadges Component

```typescript
interface TrustBadgesProps {
  /** Trust level to display */
  trustLevel: 'official' | 'verified' | 'community';
  /** Optional source URL/identifier (shown in tooltip) */
  source?: string;
  /** Optional className for styling */
  className?: string;
}
```

### getTrustLevelFromSource Helper

```typescript
function getTrustLevelFromSource(source: string): TrustLevel;
```

Determines trust level from source string using pattern matching:
- **Official**: Contains `anthropic/`, `anthropics/`, or starts with `claude-`
- **Verified**: Starts with `verified/` or `trusted-`
- **Community**: All other sources

## Integration Examples

### With Artifact Card

```tsx
import { TrustBadges, getTrustLevelFromSource } from '@/components/TrustBadges';

function ArtifactCard({ artifact }) {
  const trustLevel = getTrustLevelFromSource(artifact.source);

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between">
          <CardTitle>{artifact.name}</CardTitle>
          <div className="flex gap-1">
            <Badge>{artifact.type}</Badge>
            <TrustBadges trustLevel={trustLevel} source={artifact.source} />
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* ... */}
      </CardContent>
    </Card>
  );
}
```

### With UnifiedCard Component

See `TrustBadges.integration.md` for detailed integration guide.

## Accessibility

The component follows WCAG 2.1 AA standards:

- **aria-label**: Descriptive label on badge element
- **Keyboard focus**: Tooltips are keyboard accessible
- **Color contrast**: High contrast for readability
- **Screen readers**: Meaningful labels and tooltips

## Testing

Run tests:

```bash
pnpm test TrustBadges.test.tsx
```

Test coverage:
- Badge rendering (3 trust levels)
- Tooltip display and content
- Source auto-detection (official/verified/community)
- Edge cases and protocols
- Custom className support

**Result**: 21 tests, all passing ✓

## Design Decisions

### Why separate from marketplace TrustBadge?

The marketplace `TrustBadge` (in `source-card.tsx`) uses different trust levels:
- `untrusted`, `basic`, `verified`, `official`

This component uses artifact-specific trust levels:
- `official`, `verified`, `community`

### Why use icons?

Icons provide quick visual recognition:
- **ShieldCheck** (✓): Official and Verified sources
- **Shield**: Community sources

### Why tooltips?

Tooltips provide additional context without cluttering the UI:
- Trust level explanation
- Source URL/identifier
- Educational for new users

## Future Enhancements

Potential improvements for future phases:

- [ ] Multiple trust badges on same artifact
- [ ] Trust level change animations
- [ ] Custom trust level configurations
- [ ] Trust level history tracking
- [ ] Integration with artifact scoring system

## Related Components

- **marketplace/source-card.tsx**: TrustBadge for GitHub sources
- **shared/unified-card.tsx**: Universal artifact/entity card (integration target)
- **ui/badge.tsx**: Base badge component

## Support

For questions or issues:
- See examples: `TrustBadges.example.tsx`
- See integration guide: `TrustBadges.integration.md`
- Check tests: `__tests__/components/TrustBadges.test.tsx`
