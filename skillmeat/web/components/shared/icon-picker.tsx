'use client';

import dynamic from 'next/dynamic';
import { Skeleton } from '@/components/ui/skeleton';
import { DEFAULT_ICONS } from '@/lib/icon-constants';
import { useIconPacks } from '@/hooks';
import type { IconName } from '@/components/ui/icon-picker';
import type { IconData } from '@/components/ui/icon-picker';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface IconPickerProps {
  value: string;
  onChange: (iconName: string) => void;
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Dynamic import — avoids SSR for the heavy icon picker bundle
// ---------------------------------------------------------------------------

const ShadcnIconPicker = dynamic(
  () => import('@/components/ui/icon-picker').then((mod) => mod.IconPicker),
  {
    ssr: false,
    loading: () => <Skeleton className="h-9 w-full rounded-md" />,
  }
);

// ---------------------------------------------------------------------------
// Fallback trigger
// ---------------------------------------------------------------------------

function FallbackTrigger({
  value,
  disabled,
}: {
  value: string;
  disabled: boolean;
}) {
  const matched = DEFAULT_ICONS.find((icon) => icon.name === value);
  const displayName = matched?.label ?? value ?? 'Select icon';

  return (
    <div
      className="flex h-9 w-full items-center gap-2 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
      aria-label={`Selected icon: ${displayName}`}
      aria-disabled={disabled}
    >
      <span className="text-muted-foreground">{displayName}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Shared icon picker that wraps the shadcn-iconpicker component.
 *
 * - Loads icon packs from `useIconPacks()` to filter displayed icons.
 * - Uses `next/dynamic` with `ssr: false` for code splitting.
 * - Falls back to the raw `ShadcnIconPicker` (all Lucide icons) when pack
 *   data is unavailable or no packs are enabled.
 * - Shows a skeleton while the dynamic import is resolving.
 */
export function IconPicker({ value, onChange, disabled = false }: IconPickerProps) {
  const { data: iconPacks, isLoading: isLoadingPacks } = useIconPacks();

  // Derive the filtered icon list from enabled packs.
  // Each IconPack.icons has { name, label? } — we need to produce IconData[]
  // which needs at least { name }.  The shadcn picker accepts any iconsList
  // with a `name` field.
  const iconsList: IconData[] | undefined = (() => {
    if (!iconPacks) return undefined;

    const enabledPacks = iconPacks.filter((p) => p.enabled);
    if (enabledPacks.length === 0) return undefined;

    // Deduplicate by name across enabled packs.
    const seen = new Set<string>();
    const icons: IconData[] = [];

    for (const pack of enabledPacks) {
      for (const icon of pack.icons ?? []) {
        if (!seen.has(icon.name)) {
          seen.add(icon.name);
          // Cast to IconData — name is the required field; tags/categories are optional.
          icons.push({ name: icon.name } as IconData);
        }
      }
    }

    return icons.length > 0 ? icons : undefined;
  })();

  // While packs are loading, show a skeleton.
  if (isLoadingPacks) {
    return <Skeleton className="h-9 w-full rounded-md" />;
  }

  return (
    <ShadcnIconPicker
      value={value as IconName}
      onValueChange={(iconName: IconName) => onChange(iconName)}
      iconsList={iconsList}
      modal={false}
      triggerPlaceholder="Select an icon"
    >
      {disabled ? (
        <FallbackTrigger value={value} disabled={disabled} />
      ) : undefined}
    </ShadcnIconPicker>
  );
}
