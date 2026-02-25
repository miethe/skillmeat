'use client';

import { Info } from 'lucide-react';
import { useIconPacks, usePatchIconPacks } from '@/hooks';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { Label } from '@/components/ui/label';
import type { IconPack } from '@/lib/icon-constants';

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function IconPackListSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading icon packs">
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="flex items-center justify-between rounded-lg border border-border p-4">
          <div className="space-y-1.5">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
          <Skeleton className="h-5 w-9 rounded-full" />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function IconPackEmptyState() {
  return (
    <div
      className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-muted-foreground/30 px-4 py-12 text-center"
      role="status"
      aria-label="No icon packs available"
    >
      <p className="text-sm font-medium text-muted-foreground">No icon packs available</p>
      <p className="max-w-xs text-xs text-muted-foreground/70">
        Icon packs will appear here when configured on the server.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Individual icon pack row
// ---------------------------------------------------------------------------

interface IconPackRowProps {
  pack: IconPack;
  onToggle: (pack: IconPack, enabled: boolean) => void;
  isPending: boolean;
}

function IconPackRow({ pack, onToggle, isPending }: IconPackRowProps) {
  const switchId = `icon-pack-toggle-${pack.id}`;
  const iconCount = pack.icons.length;

  return (
    <div
      className="flex items-center justify-between gap-4 rounded-lg border border-border p-4 transition-colors hover:bg-muted/30"
      role="listitem"
    >
      <div className="flex-1 space-y-0.5">
        <Label
          htmlFor={switchId}
          className="cursor-pointer text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
        >
          {pack.name}
        </Label>
        <p className="text-xs text-muted-foreground">
          {iconCount.toLocaleString()} icon{iconCount !== 1 ? 's' : ''}
        </p>
      </div>

      <Switch
        id={switchId}
        checked={pack.enabled}
        onCheckedChange={(checked) => onToggle(pack, checked)}
        disabled={isPending}
        aria-label={`${pack.enabled ? 'Disable' : 'Enable'} ${pack.name}`}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * IconsSettings — icon pack management panel.
 *
 * Renders a list of all available icon packs from useIconPacks() with an
 * enabled/disabled toggle for each. Toggling calls usePatchIconPacks() with
 * a single-entry patch. Changes take effect on next icon picker open.
 */
export function IconsSettings() {
  const { data: iconPacks, isLoading } = useIconPacks();
  const patchPacks = usePatchIconPacks();

  const handleToggle = (pack: IconPack, enabled: boolean) => {
    patchPacks.mutate([{ pack_id: pack.id, enabled }]);
  };

  return (
    <div className="space-y-4">
      {/* Description */}
      <p className="text-sm text-muted-foreground">
        Enable or disable icon packs to control which icons are available in all icon pickers.
      </p>

      {/* Pack list */}
      {isLoading ? (
        <IconPackListSkeleton />
      ) : !iconPacks || iconPacks.length === 0 ? (
        <IconPackEmptyState />
      ) : (
        <div className="space-y-2" role="list" aria-label="Icon packs">
          {iconPacks.map((pack) => (
            <IconPackRow
              key={pack.id}
              pack={pack}
              onToggle={handleToggle}
              isPending={patchPacks.isPending}
            />
          ))}
        </div>
      )}

      {/* Informational note */}
      <div
        className="flex items-start gap-2 rounded-md border border-border bg-muted/40 px-3 py-2.5"
        role="note"
        aria-label="Icon pack change notice"
      >
        <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
        <p className="text-xs text-muted-foreground">
          Changes to icon pack settings take effect the next time you open an icon picker dialog.
        </p>
      </div>
    </div>
  );
}
