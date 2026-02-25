'use client';

import React, { useState, useMemo } from 'react';
import { Info, Search, X, Loader2, Plus, Upload, Link, Trash2 } from 'lucide-react';
import { DynamicIcon } from 'lucide-react/dynamic';
import { useIconPacks, usePatchIconPacks, useInstallIconPackFromUrl, useInstallIconPackFromFile, useDeleteIconPack } from '@/hooks';
import { Switch } from '@/components/ui/switch';
import { Skeleton } from '@/components/ui/skeleton';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { iconsData } from '@/components/ui/icons-data';
import { toast } from 'sonner';
import type { IconPack } from '@/lib/icon-constants';

// ---------------------------------------------------------------------------
// Icon count helper
// ---------------------------------------------------------------------------

/**
 * Returns the number of icons for a given pack.
 * Currently all packs map to the full Lucide dataset (iconsData).
 * Per-pack filtering can be wired here once pack-level metadata is available.
 */
function getIconCount(_packId: string): number {
  return iconsData.length;
}

// ---------------------------------------------------------------------------
// All unique categories derived from iconsData
// ---------------------------------------------------------------------------

const ALL_CATEGORIES: string[] = ['All', ...Array.from(
  new Set(iconsData.flatMap((icon) => icon.categories))
).sort()];

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
// Icon pack viewer dialog
// ---------------------------------------------------------------------------

interface IconPackViewerDialogProps {
  pack: IconPack;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function IconPackViewerDialog({ pack, open, onOpenChange }: IconPackViewerDialogProps) {
  const [activeCategory, setActiveCategory] = useState<string>('All');
  const [search, setSearch] = useState('');

  const filteredIcons = useMemo(() => {
    const categoryFiltered =
      activeCategory === 'All'
        ? iconsData
        : iconsData.filter((icon) => icon.categories.includes(activeCategory));

    if (!search.trim()) return categoryFiltered;

    const term = search.toLowerCase();
    return categoryFiltered.filter(
      (icon) =>
        icon.name.toLowerCase().includes(term) ||
        icon.tags.some((tag) => tag.toLowerCase().includes(term))
    );
  }, [activeCategory, search]);

  const totalCount = getIconCount(pack.id);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="flex max-h-[90vh] max-w-5xl flex-col gap-0 p-0"
        aria-label={`Icon viewer for ${pack.name}`}
      >
        {/* Header */}
        <DialogHeader className="shrink-0 border-b border-border px-6 py-4">
          <DialogTitle className="flex items-center gap-3">
            <span>{pack.name}</span>
            <span className="text-sm font-normal text-muted-foreground">
              {totalCount.toLocaleString()} icons
            </span>
          </DialogTitle>
        </DialogHeader>

        {/* Body: sidebar + main */}
        <div className="flex min-h-0 flex-1">
          {/* Category sidebar */}
          <nav
            className="w-44 shrink-0 border-r border-border"
            aria-label="Icon categories"
          >
            <ScrollArea className="h-[80vh]">
              <ul className="py-2" role="list">
                {ALL_CATEGORIES.map((cat) => (
                  <li key={cat} role="listitem">
                    <button
                      className={`w-full px-4 py-1.5 text-left text-sm transition-colors hover:bg-muted/60 ${
                        activeCategory === cat
                          ? 'bg-muted font-medium text-foreground'
                          : 'text-muted-foreground'
                      }`}
                      onClick={() => {
                        setActiveCategory(cat);
                        setSearch('');
                      }}
                      aria-pressed={activeCategory === cat}
                    >
                      {cat}
                    </button>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          </nav>

          {/* Main icon area */}
          <div className="flex min-w-0 flex-1 flex-col">
            {/* Search bar */}
            <div className="shrink-0 border-b border-border px-4 py-3">
              <div className="relative">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
                <Input
                  type="search"
                  placeholder="Search icons…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="h-8 pl-8 pr-8 text-sm"
                  aria-label="Search icons"
                />
                {search && (
                  <button
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    onClick={() => setSearch('')}
                    aria-label="Clear search"
                  >
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                )}
              </div>
              <p className="mt-1.5 text-xs text-muted-foreground">
                {filteredIcons.length.toLocaleString()} icon{filteredIcons.length !== 1 ? 's' : ''}
                {activeCategory !== 'All' && ` in ${activeCategory}`}
                {search && ` matching "${search}"`}
              </p>
            </div>

            {/* Icon grid */}
            <ScrollArea className="flex-1" style={{ height: 'calc(80vh - 57px)' }}>
              {filteredIcons.length === 0 ? (
                <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">
                  No icons found
                </div>
              ) : (
                <div
                  className="grid grid-cols-8 gap-1 p-4 sm:grid-cols-10 lg:grid-cols-12"
                  role="list"
                  aria-label={`Icons${activeCategory !== 'All' ? ` in ${activeCategory}` : ''}`}
                >
                  {filteredIcons.map((icon) => (
                    <div
                      key={icon.name}
                      className="flex flex-col items-center gap-1 rounded-md p-1.5 text-center transition-colors hover:bg-muted/60"
                      role="listitem"
                      title={icon.name}
                    >
                      <DynamicIcon
                        name={icon.name as Parameters<typeof DynamicIcon>[0]['name']}
                        size={20}
                        className="shrink-0 text-foreground"
                        aria-hidden="true"
                      />
                      <span className="w-full truncate text-[9px] leading-tight text-muted-foreground">
                        {icon.name}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ---------------------------------------------------------------------------
// Add icon pack dialog
// ---------------------------------------------------------------------------

interface AddIconPackDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function AddIconPackDialog({ open, onOpenChange }: AddIconPackDialogProps) {
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const installFromUrl = useInstallIconPackFromUrl();
  const installFromFile = useInstallIconPackFromFile();

  const isPending = installFromUrl.isPending || installFromFile.isPending;

  function resetState() {
    setUrl('');
    setFile(null);
    setSuccess(false);
    setError(null);
    installFromUrl.reset();
    installFromFile.reset();
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) resetState();
    onOpenChange(nextOpen);
  }

  async function handleUrlInstall(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await installFromUrl.mutateAsync(url);
      setSuccess(true);
      toast.success('Icon pack installed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to install icon pack');
    }
  }

  async function handleFileInstall(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    try {
      await installFromFile.mutateAsync(file);
      setSuccess(true);
      toast.success('Icon pack installed');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to install icon pack');
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md" aria-label="Add icon pack">
        <DialogHeader>
          <DialogTitle>Add Icon Pack</DialogTitle>
        </DialogHeader>

        {success ? (
          <div className="space-y-4">
            <Alert>
              <AlertTitle>Pack installed</AlertTitle>
              <AlertDescription>
                The icon picker has been updated. You may need to refresh if icons don&apos;t appear
                immediately.
              </AlertDescription>
            </Alert>
            <Button className="w-full" onClick={() => handleOpenChange(false)}>
              Close
            </Button>
          </div>
        ) : (
          <Tabs defaultValue="url" onValueChange={() => setError(null)}>
            <TabsList className="w-full">
              <TabsTrigger value="url" className="flex-1 gap-1.5">
                <Link className="h-3.5 w-3.5" aria-hidden="true" />
                From URL
              </TabsTrigger>
              <TabsTrigger value="file" className="flex-1 gap-1.5">
                <Upload className="h-3.5 w-3.5" aria-hidden="true" />
                Upload File
              </TabsTrigger>
            </TabsList>

            <TabsContent value="url" className="mt-4">
              <form onSubmit={handleUrlInstall} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="icon-pack-url">Pack URL</Label>
                  <Input
                    id="icon-pack-url"
                    type="url"
                    placeholder="https://example.com/icon-pack.json"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isPending}
                    required
                    aria-describedby={error ? 'add-pack-error' : undefined}
                  />
                </div>
                {error && (
                  <p id="add-pack-error" className="text-sm text-destructive" role="alert">
                    {error}
                  </p>
                )}
                <Button type="submit" className="w-full" disabled={isPending || !url.trim()}>
                  {isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                      Installing…
                    </>
                  ) : (
                    'Install'
                  )}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="file" className="mt-4">
              <form onSubmit={handleFileInstall} className="space-y-4">
                <div className="space-y-1.5">
                  <Label htmlFor="icon-pack-file">Pack file (.json)</Label>
                  <Input
                    id="icon-pack-file"
                    type="file"
                    accept=".json"
                    onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    disabled={isPending}
                    aria-describedby={error ? 'add-pack-error-file' : undefined}
                  />
                </div>
                {error && (
                  <p id="add-pack-error-file" className="text-sm text-destructive" role="alert">
                    {error}
                  </p>
                )}
                <Button type="submit" className="w-full" disabled={isPending || !file}>
                  {isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                      Installing…
                    </>
                  ) : (
                    'Install'
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        )}
      </DialogContent>
    </Dialog>
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
  const [viewerOpen, setViewerOpen] = useState(false);
  const deleteIconPack = useDeleteIconPack();
  const switchId = `icon-pack-toggle-${pack.id}`;
  const iconCount = getIconCount(pack.id);
  const isAnyPending = isPending || deleteIconPack.isPending;

  async function handleDelete(e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await deleteIconPack.mutateAsync(pack.id);
      toast.success('Icon pack removed');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Failed to remove icon pack');
    }
  }

  return (
    <>
      <div
        className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-border p-4 transition-colors hover:bg-muted/30"
        role="listitem"
        onClick={() => setViewerOpen(true)}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setViewerOpen(true);
          }
        }}
        aria-label={`View icons in ${pack.name}`}
      >
        <div className="flex-1 space-y-0.5">
          <Label
            htmlFor={switchId}
            className="pointer-events-none text-sm font-medium leading-none"
          >
            {pack.name}
          </Label>
          <p className="text-xs text-muted-foreground">
            {iconCount.toLocaleString()} icon{iconCount !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <Switch
            id={switchId}
            checked={pack.enabled}
            onCheckedChange={(checked) => onToggle(pack, checked)}
            disabled={isAnyPending}
            aria-label={`${pack.enabled ? 'Disable' : 'Enable'} ${pack.name}`}
          />

          {pack.id !== 'lucide-default' && (
            <Button
              variant="ghost"
              size="icon"
              aria-label="Remove icon pack"
              disabled={isAnyPending}
              onClick={handleDelete}
            >
              {deleteIconPack.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              )}
            </Button>
          )}
        </div>
      </div>

      <IconPackViewerDialog
        pack={pack}
        open={viewerOpen}
        onOpenChange={setViewerOpen}
      />
    </>
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
 *
 * Clicking a pack row opens an IconPackViewerDialog showing all icons in the
 * pack, browseable by category with a name/tag search filter.
 */
export function IconsSettings() {
  const { data: iconPacks, isLoading } = useIconPacks();
  const patchPacks = usePatchIconPacks();
  const [addDialogOpen, setAddDialogOpen] = React.useState(false);

  const handleToggle = (pack: IconPack, enabled: boolean) => {
    patchPacks.mutate([{ pack_id: pack.id, enabled }]);
  };

  return (
    <div className="space-y-4">
      {/* Header row: description + Add Pack button */}
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          Enable or disable icon packs to control which icons are available in all icon pickers.
          Click a pack to browse its icons.
        </p>
        <Button
          variant="outline"
          size="sm"
          className="shrink-0 gap-1.5"
          onClick={() => setAddDialogOpen(true)}
          aria-label="Add icon pack"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          Add Pack
        </Button>
      </div>

      <AddIconPackDialog open={addDialogOpen} onOpenChange={setAddDialogOpen} />

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
