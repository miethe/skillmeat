# Sync Components

Components for displaying drift detection and synchronization status.

## ChangeBadge

Displays the origin of changes detected between upstream and local artifact versions.

### Usage

```tsx
import { ChangeBadge } from '@/components/sync';

// Basic usage
<ChangeBadge origin="upstream" />
<ChangeBadge origin="local" />
<ChangeBadge origin="both" />
<ChangeBadge origin="none" />

// Size variants
<ChangeBadge origin="upstream" size="sm" />
<ChangeBadge origin="local" size="md" />  // default
<ChangeBadge origin="both" size="lg" />

// Icon only (no label)
<ChangeBadge origin="upstream" showLabel={false} />

// Custom className
<ChangeBadge origin="conflict" className="ml-2" />
```

### Props

```typescript
interface ChangeBadgeProps {
  origin: ChangeOrigin;      // Required: 'upstream' | 'local' | 'both' | 'none'
  size?: 'sm' | 'md' | 'lg'; // Optional: Badge size (default: 'md')
  showLabel?: boolean;        // Optional: Show text label (default: true)
  className?: string;         // Optional: Additional CSS classes
}
```

### Change Origin Types

| Origin | Color | Icon | Meaning |
|--------|-------|------|---------|
| `upstream` | Blue | ↓ | Changes only in upstream source |
| `local` | Amber/Yellow | ✎ | Local modifications only |
| `both` | Red | ⚠ | Changes in both (conflict) |
| `none` | Gray | ✓ | No changes detected |

### Dark Mode

All color variants include dark mode support using Tailwind's `dark:` variant.

### Examples in Context

**Drift detection list**:
```tsx
{artifacts.map(artifact => (
  <div key={artifact.id} className="flex items-center gap-2">
    <span>{artifact.name}</span>
    <ChangeBadge origin={artifact.change_origin} size="sm" />
  </div>
))}
```

**Conflict warning**:
```tsx
{artifact.change_origin === 'both' && (
  <div className="flex items-center gap-2 p-4 bg-red-50 rounded">
    <ChangeBadge origin="both" />
    <span>This artifact has conflicts that require manual merge</span>
  </div>
)}
```

### Dependencies

- `@/components/ui/badge` - shadcn/ui Badge primitive
- `@/lib/utils` - `cn()` utility for className merging
- `@/types/drift` - `ChangeOrigin` type definition
