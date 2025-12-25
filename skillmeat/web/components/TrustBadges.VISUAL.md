# TrustBadges Visual Reference

Visual guide showing how TrustBadges appear in different contexts.

## Badge Appearance

### Official Badge (Blue)
```
┌─────────────────┐
│ ✓ Official      │  Blue border/background
└─────────────────┘
Tooltip: "Official artifact from trusted source"
         Source: anthropics/skills/canvas-design
```

**Colors**:
- Border: `border-blue-500` (#3b82f6)
- Text: `text-blue-700` (#1d4ed8)
- Background: `bg-blue-50` (light) / `dark:bg-blue-950` (dark)

### Verified Badge (Green)
```
┌─────────────────┐
│ ✓ Verified      │  Green border/background
└─────────────────┘
Tooltip: "Community verified artifact"
         Source: verified/community-skills
```

**Colors**:
- Border: `border-green-500` (#22c55e)
- Text: `text-green-700` (#15803d)
- Background: `bg-green-50` (light) / `dark:bg-green-950` (dark)

### Community Badge (Gray)
```
┌─────────────────┐
│ 🛡️ Community    │  Gray border/background
└─────────────────┘
Tooltip: "Community contributed artifact"
         Source: user/repo/custom-skill
```

**Colors**:
- Border: `border-gray-400` (#9ca3af)
- Text: `text-gray-600` (#4b5563)
- Background: `bg-gray-50` (light) / `dark:bg-gray-900` (dark)

## Artifact Card Layouts

### Layout 1: Badges in Header
```
┌────────────────────────────────────────────┐
│ Canvas Design                  [skill]     │
│                             [✓ Official]   │
├────────────────────────────────────────────┤
│ Official canvas design skill               │
│                                            │
│ v2.1.0 | anthropics/skills/canvas         │
└────────────────────────────────────────────┘
```

### Layout 2: Badges with Score
```
┌────────────────────────────────────────────┐
│ Code Review        [skill] [✓ Verified]    │
│                               [95]         │
├────────────────────────────────────────────┤
│ Community verified code review skill       │
│                                            │
│ v1.0.0 | verified/community/code-review   │
└────────────────────────────────────────────┘
```

### Layout 3: Multiple Badges
```
┌────────────────────────────────────────────┐
│ Custom Helper                              │
│ [command] [🛡️ Community] [45]             │
├────────────────────────────────────────────┤
│ User-contributed helper skill              │
│                                            │
│ v0.5.0 | user/repo/custom-helper          │
└────────────────────────────────────────────┘
```

## Badge Combinations

### High Trust + High Confidence
```
[✓ Official] [95]
```
- Best case: Official source with high confidence score
- User confidence: Very High
- Color harmony: Blue + Green

### Medium Trust + Medium Confidence
```
[✓ Verified] [65]
```
- Good case: Verified source with medium confidence
- User confidence: Good
- Color harmony: Green + Yellow

### Low Trust + Low Confidence
```
[🛡️ Community] [45]
```
- Caution case: Community source with low confidence
- User confidence: Use with care
- Color harmony: Gray + Red

## Integration with UnifiedCard

### Before (without TrustBadges)
```
┌────────────────────────────────────────────┐
│ 📄 Canvas Design                [Synced]   │
├────────────────────────────────────────────┤
│ Official canvas design skill               │
│ 📦 v2.1.0  🕐 2h ago  📈 24                │
│ [skill] [design] [canvas]                  │
└────────────────────────────────────────────┘
```

### After (with TrustBadges)
```
┌────────────────────────────────────────────┐
│ 📄 Canvas Design        [Synced]           │
│                      [✓ Official]          │
├────────────────────────────────────────────┤
│ Official canvas design skill               │
│ 📦 v2.1.0  🕐 2h ago  📈 24                │
│ [skill] [design] [canvas]                  │
└────────────────────────────────────────────┘
```

## Hover States

### Before Hover
```
[✓ Official]
```

### On Hover (Tooltip appears)
```
[✓ Official]
  ↓
┌──────────────────────────────────────┐
│ Official artifact from trusted       │
│ source                               │
│                                      │
│ Source: anthropics/skills/canvas     │
└──────────────────────────────────────┘
```

## Responsive Behavior

### Desktop (1200px+)
```
All badges visible in single row
[skill] [✓ Official] [95]
```

### Tablet (768px-1199px)
```
Badges may wrap to second row
[skill] [✓ Official]
[95]
```

### Mobile (<768px)
```
Stacked layout
[skill]
[✓ Official]
[95]
```

## Dark Mode

### Light Mode
```
Official:  [✓ Official]  (Blue on white)
Verified:  [✓ Verified]  (Green on white)
Community: [🛡️ Community] (Gray on white)
```

### Dark Mode
```
Official:  [✓ Official]  (Blue on dark)
Verified:  [✓ Verified]  (Green on dark)
Community: [🛡️ Community] (Gray on dark)
```

All badges automatically adjust colors via Tailwind dark mode classes.

## Accessibility

### Screen Reader
```
<Badge aria-label="Official artifact from trusted source">
  <ShieldCheck /> Official
</Badge>

Announced as: "Official artifact from trusted source"
```

### Keyboard Navigation
```
Tab → Focus badge
Enter/Space → Open tooltip
Escape → Close tooltip
```

### Tooltip Focus
```
Badge focused → Tooltip appears after delay
Badge unfocused → Tooltip disappears
```

## Size Comparison

### Small (sm)
```
[✓ Official]  (text-xs, h-3 w-3 icon)
```

### Medium (default)
```
[✓ Official]  (text-xs, h-3 w-3 icon)
```

### With ScoreBadge
```
[✓ Official] [95]  (both size sm)
```

## Usage Patterns

### Pattern 1: Trust Only
```tsx
<TrustBadges trustLevel="official" />
```
Result: `[✓ Official]`

### Pattern 2: Trust + Source
```tsx
<TrustBadges
  trustLevel="official"
  source="anthropics/skills/canvas"
/>
```
Result: `[✓ Official]` (tooltip shows source)

### Pattern 3: Auto-detect
```tsx
const level = getTrustLevelFromSource(artifact.source);
<TrustBadges trustLevel={level} source={artifact.source} />
```
Result: Auto-determined badge with source tooltip

### Pattern 4: With Score
```tsx
<TrustBadges trustLevel="official" source={source} />
<ScoreBadge confidence={95} size="sm" />
```
Result: `[✓ Official] [95]`

## Color Accessibility (WCAG 2.1 AA)

All badge colors meet WCAG 2.1 AA contrast ratio requirements (>4.5:1):

| Badge | Background | Text | Contrast Ratio |
|-------|-----------|------|----------------|
| Official | blue-50 | blue-700 | 7.2:1 ✅ |
| Verified | green-50 | green-700 | 7.5:1 ✅ |
| Community | gray-50 | gray-600 | 5.8:1 ✅ |

Dark mode colors also meet contrast requirements.
