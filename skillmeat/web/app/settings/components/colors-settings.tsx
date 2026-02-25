'use client';

import { useState, useRef, useEffect } from 'react';
import { Plus, Trash2, Pencil, HardDriveDownload, X } from 'lucide-react';
import { useCustomColors, useCreateCustomColor, useDeleteCustomColor, useUpdateCustomColor } from '@/hooks';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { cn } from '@/lib/utils';
import { isValidHex } from '@/lib/color-constants';
import type { ColorResponse } from '@/lib/api/colors';

// ---------------------------------------------------------------------------
// LocalStorage migration key
// ---------------------------------------------------------------------------

const LS_LEGACY_KEY = 'skillmeat-group-custom-colors-v1';

// ---------------------------------------------------------------------------
// Migration banner
// ---------------------------------------------------------------------------

interface MigrationBannerProps {
  onMigrate: () => Promise<void>;
  onDismiss: () => void;
  isMigrating: boolean;
}

function MigrationBanner({ onMigrate, onDismiss, isMigrating }: MigrationBannerProps) {
  return (
    <Alert className="relative flex items-start gap-3 border-amber-500/40 bg-amber-500/5 text-amber-900 dark:text-amber-200">
      <HardDriveDownload className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden="true" />
      <AlertDescription className="flex flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <span className="text-sm">
          You have custom colors saved locally. Migrate them to sync across devices?
        </span>
        <div className="flex shrink-0 gap-2">
          <Button
            size="sm"
            variant="outline"
            className="border-amber-500/40 bg-transparent text-amber-800 hover:bg-amber-500/10 hover:text-amber-900 dark:text-amber-200 dark:hover:text-amber-100"
            onClick={() => void onMigrate()}
            disabled={isMigrating}
          >
            {isMigrating ? 'Migrating…' : 'Migrate'}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-amber-800/60 hover:bg-amber-500/10 hover:text-amber-800 dark:text-amber-400/60 dark:hover:text-amber-300"
            onClick={onDismiss}
            disabled={isMigrating}
            aria-label="Dismiss migration banner"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function ColorGridSkeleton() {
  return (
    <div
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4"
      aria-busy="true"
      aria-label="Loading custom colors"
    >
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-20 rounded-lg" />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function ColorEmptyState() {
  return (
    <div
      className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-muted-foreground/30 px-4 py-12 text-center"
      role="status"
      aria-label="No custom colors"
    >
      <div
        className="flex h-10 w-10 items-center justify-center rounded-full bg-muted"
        aria-hidden="true"
      >
        <div className="h-5 w-5 rounded-full bg-gradient-to-br from-rose-400 via-violet-400 to-cyan-400 opacity-70" />
      </div>
      <p className="text-sm font-medium text-muted-foreground">No custom colors yet</p>
      <p className="max-w-xs text-xs text-muted-foreground/70">
        Add your own colors to use across deployment sets, groups, and more.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Color swatch card
// ---------------------------------------------------------------------------

interface ColorSwatchCardProps {
  color: ColorResponse;
  onDelete: (color: ColorResponse) => void;
  onRename: (id: string, name: string) => void;
}

function ColorSwatchCard({ color, onDelete, onRename }: ColorSwatchCardProps) {
  const [isEditingName, setIsEditingName] = useState(false);
  const [nameValue, setNameValue] = useState(color.name ?? '');
  const inputRef = useRef<HTMLInputElement>(null);

  const handleStartEdit = () => {
    setNameValue(color.name ?? '');
    setIsEditingName(true);
    // Focus is handled via autoFocus on Input
  };

  const handleSaveName = () => {
    const trimmed = nameValue.trim();
    if (trimmed !== (color.name ?? '')) {
      onRename(color.id, trimmed);
    }
    setIsEditingName(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSaveName();
    } else if (e.key === 'Escape') {
      setNameValue(color.name ?? '');
      setIsEditingName(false);
    }
  };

  return (
    <div
      className="group relative flex flex-col gap-2 rounded-lg border border-border p-3 transition-shadow hover:shadow-sm"
      role="listitem"
    >
      {/* Swatch */}
      <div
        className="h-10 w-full rounded-md border border-border/50"
        style={{ backgroundColor: color.hex }}
        aria-label={`Color swatch: ${color.hex}`}
      />

      {/* Hex + name */}
      <div className="flex flex-col gap-0.5">
        <p className="font-mono text-xs font-medium text-foreground">{color.hex}</p>
        {isEditingName ? (
          <Input
            ref={inputRef}
            autoFocus
            value={nameValue}
            onChange={(e) => setNameValue(e.target.value)}
            onBlur={handleSaveName}
            onKeyDown={handleKeyDown}
            className="h-6 px-1 py-0 text-xs"
            aria-label="Edit color name"
          />
        ) : (
          <button
            type="button"
            onClick={handleStartEdit}
            className={cn(
              'text-left text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring',
              !color.name && 'italic text-muted-foreground/50'
            )}
            aria-label={color.name ? `Rename ${color.name}` : 'Add a name'}
          >
            {color.name ? color.name : 'Add a name…'}
          </button>
        )}
      </div>

      {/* Hover actions */}
      <div className="absolute right-2 top-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 shadow-sm"
          onClick={handleStartEdit}
          aria-label={`Rename color ${color.hex}`}
        >
          <Pencil className="h-3 w-3" aria-hidden="true" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0 text-destructive shadow-sm hover:bg-destructive/10 hover:text-destructive"
          onClick={() => onDelete(color)}
          aria-label={`Delete color ${color.hex}`}
        >
          <Trash2 className="h-3 w-3" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Add color popover
// ---------------------------------------------------------------------------

interface AddColorPopoverProps {
  onAdd: (hex: string) => Promise<void>;
  isPending: boolean;
}

function AddColorPopover({ onAdd, isPending }: AddColorPopoverProps) {
  const [open, setOpen] = useState(false);
  const [hexInput, setHexInput] = useState('#');

  const normalizedHex = hexInput.trim().startsWith('#') ? hexInput.trim() : `#${hexInput.trim()}`;
  const isValid = isValidHex(normalizedHex);
  const previewColor = isValid ? normalizedHex : undefined;

  const handleSubmit = async () => {
    if (!isValid) return;
    await onAdd(normalizedHex.toLowerCase());
    setHexInput('#');
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      void handleSubmit();
    }
  };

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Plus className="h-4 w-4" aria-hidden="true" />
          Add Color
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-64 p-4" align="end">
        <p className="mb-3 text-sm font-medium">Add a custom color</p>
        <div className="flex items-center gap-2">
          {/* Color preview swatch */}
          <div
            className={cn(
              'h-9 w-9 shrink-0 rounded-md border transition-colors',
              previewColor ? 'border-border' : 'border-dashed border-muted-foreground/40 bg-muted'
            )}
            style={previewColor ? { backgroundColor: previewColor } : undefined}
            aria-hidden="true"
          />
          <Input
            autoFocus
            placeholder="#ff6b6b"
            value={hexInput}
            onChange={(e) => setHexInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="font-mono text-sm"
            aria-label="Hex color value"
          />
        </div>
        {hexInput.length > 1 && !isValid && (
          <p className="mt-1.5 text-xs text-destructive" role="alert">
            Enter a valid hex color (e.g. #ff6b6b)
          </p>
        )}
        <div className="mt-3 flex gap-2">
          <Button
            size="sm"
            className="flex-1"
            onClick={() => void handleSubmit()}
            disabled={!isValid || isPending}
          >
            {isPending ? 'Adding…' : 'Add Color'}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              setHexInput('#');
              setOpen(false);
            }}
          >
            Cancel
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

/**
 * ColorsSettings — custom color management panel.
 *
 * Renders a palette grid of user-defined custom colors from useCustomColors().
 * Supports inline rename, add via hex popover, and delete with AlertDialog
 * confirmation.
 */
export function ColorsSettings() {
  const { data: customColors, isLoading } = useCustomColors();
  const createColor = useCreateCustomColor();
  const deleteColor = useDeleteCustomColor();
  const updateColor = useUpdateCustomColor();

  const [pendingDelete, setPendingDelete] = useState<ColorResponse | null>(null);

  // ── LocalStorage migration banner ────────────────────────────────────────
  const [showMigrationBanner, setShowMigrationBanner] = useState(false);
  const [isMigrating, setIsMigrating] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(LS_LEGACY_KEY);
      if (stored) {
        setShowMigrationBanner(true);
      }
    } catch {
      // localStorage unavailable (e.g. SSR or privacy mode) — silently ignore
    }
  }, []);

  const handleMigrate = async () => {
    setIsMigrating(true);
    try {
      const raw = localStorage.getItem(LS_LEGACY_KEY);
      if (!raw) {
        setShowMigrationBanner(false);
        return;
      }

      let colors: string[];
      try {
        const parsed = JSON.parse(raw) as unknown;
        colors = Array.isArray(parsed)
          ? (parsed as unknown[]).filter((v): v is string => typeof v === 'string')
          : [];
      } catch {
        // Malformed JSON — remove the key and hide the banner
        localStorage.removeItem(LS_LEGACY_KEY);
        setShowMigrationBanner(false);
        return;
      }

      // Migrate each color; skip duplicates gracefully
      for (const hex of colors) {
        const normalised = hex.trim().startsWith('#') ? hex.trim() : `#${hex.trim()}`;
        if (!isValidHex(normalised)) continue;
        try {
          await createColor.mutateAsync({ hex: normalised.toLowerCase() });
        } catch {
          // Duplicate or other error — skip and continue
        }
      }

      localStorage.removeItem(LS_LEGACY_KEY);
      setShowMigrationBanner(false);
    } finally {
      setIsMigrating(false);
    }
  };

  const handleDismissMigration = () => {
    // Hides the banner only; does NOT remove localStorage so user can migrate later
    setShowMigrationBanner(false);
  };

  const handleAdd = async (hex: string) => {
    await createColor.mutateAsync({ hex });
  };

  const handleConfirmDelete = async () => {
    if (!pendingDelete) return;
    await deleteColor.mutateAsync(pendingDelete.id);
    setPendingDelete(null);
  };

  const handleRename = (id: string, name: string) => {
    updateColor.mutate({ id, data: { name: name || undefined } });
  };

  return (
    <div className="space-y-4">
      {/* LocalStorage migration banner */}
      {showMigrationBanner && (
        <MigrationBanner
          onMigrate={handleMigrate}
          onDismiss={handleDismissMigration}
          isMigrating={isMigrating}
        />
      )}

      {/* Header row */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            Custom colors appear alongside presets in all color pickers throughout SkillMeat.
          </p>
        </div>
        <AddColorPopover onAdd={handleAdd} isPending={createColor.isPending} />
      </div>

      {/* Content */}
      {isLoading ? (
        <ColorGridSkeleton />
      ) : !customColors || customColors.length === 0 ? (
        <ColorEmptyState />
      ) : (
        <div
          className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4"
          role="list"
          aria-label="Custom colors"
        >
          {customColors.map((color) => (
            <ColorSwatchCard
              key={color.id}
              color={color}
              onDelete={setPendingDelete}
              onRename={handleRename}
            />
          ))}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete color?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently remove{' '}
              <span className="font-mono font-medium">{pendingDelete?.hex}</span>
              {pendingDelete?.name ? ` (${pendingDelete.name})` : ''} from your custom colors. This
              action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => void handleConfirmDelete()}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
