# Shared Components (Cross-Feature Reusable UI)

Components in `components/shared/` are used by 2+ features.

## ColorSelector

Reusable color picker combining preset colors with API-fetched custom colors.

**Source**: `skillmeat/web/components/shared/color-selector.tsx`

**Props:**
- `value: string` - Currently selected color (hex or preset name)
- `onChange: (color: string) => void` - Callback when color is selected
- `className?: string` - Optional styling override

**Features:**
- Fetches custom colors via `useCustomColors()` hook
- Displays preset color grid
- Shows custom colors section when available
- Accessible color selection with visual indicators

**Used by:**
- Groups metadata editor (group color selection)
- Deployment Set create/edit dialogs (set color selection)

**Usage:**
```typescript
import { ColorSelector } from '@/components/shared/color-selector';

<div className="space-y-2">
  <label className="text-sm font-medium">Group Color</label>
  <ColorSelector value={color} onChange={onColorChange} />
</div>
```

## IconPicker

Searchable icon grid picker powered by configurable icon packs.

**Source**: `skillmeat/web/components/shared/icon-picker.tsx`

**Props:**
- `value: string` - Currently selected icon name
- `onChange: (icon: string) => void` - Callback when icon is selected
- `className?: string` - Optional styling override

**Features:**
- Loads icon packs from `icon-packs.config.json`
- Searchable with real-time filtering
- Pack selection/filtering tabs
- Visual icon preview with selection indicator

**Used by:**
- Groups metadata editor (group icon selection)
- Deployment Set create/edit dialogs (set icon selection)

**Usage:**
```typescript
import { IconPicker } from '@/components/shared/icon-picker';

<div className="space-y-2">
  <label className="text-sm font-medium">Group Icon</label>
  <IconPicker value={icon} onChange={onIconChange} />
</div>
```

## EntityPickerDialog

Multi-entity picker dialog for selecting from artifacts, groups, and deployment sets.

**Source**: `skillmeat/web/components/shared/entity-picker-dialog.tsx`

**See**: `.claude/context/key-context/entity-picker-patterns.md` for full documentation and integration patterns.

**Quick usage:**
```typescript
import { EntityPickerDialog } from '@/components/shared/entity-picker-dialog';

<EntityPickerDialog
  open={open}
  onOpenChange={setOpen}
  selectedIds={selected}
  onSelect={handleSelect}
  allowMultiple={true}
/>
```
