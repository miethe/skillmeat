'use client';

import { useState } from 'react';
import { Check, ChevronsUpDown, FolderPlus, Layers } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import { useCollectionContext } from '@/hooks/use-collection-context';

interface CollectionSwitcherProps {
  /** Callback triggered when "Add Collection" is clicked */
  onCreateCollection?: () => void;
  /** Additional CSS classes for the trigger button */
  className?: string;
}

/**
 * CollectionSwitcher - Dropdown component for switching between collections
 *
 * Features:
 * - Searchable dropdown with all available collections
 * - "All Collections" option to view all artifacts
 * - Shows artifact count for each collection
 * - "Add Collection" action (triggers TASK-4.4 dialog)
 * - Keyboard accessible with full navigation support
 * - Persists selection to localStorage via context
 *
 * @example
 * ```tsx
 * <CollectionSwitcher
 *   onCreateCollection={() => setShowCreateDialog(true)}
 *   className="w-[250px]"
 * />
 * ```
 */
export function CollectionSwitcher({
  onCreateCollection,
  className,
}: CollectionSwitcherProps) {
  const [open, setOpen] = useState(false);

  const {
    collections,
    selectedCollectionId,
    setSelectedCollectionId,
    isLoadingCollections,
  } = useCollectionContext();

  // Find current collection name for display
  const currentCollection = selectedCollectionId
    ? collections.find((c) => c.id === selectedCollectionId)
    : null;

  const displayName = currentCollection?.name ?? 'All Collections';

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label="Select collection"
          className={cn('w-[200px] justify-between', className)}
          disabled={isLoadingCollections}
        >
          <span className="truncate">{displayName}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0">
        <Command>
          <CommandInput placeholder="Search collections..." />
          <CommandList>
            <CommandEmpty>No collection found.</CommandEmpty>
            <CommandGroup heading="Collections">
              {/* "All Collections" option */}
              <CommandItem
                value="all"
                onSelect={() => {
                  setSelectedCollectionId(null);
                  setOpen(false);
                }}
              >
                <Layers className="mr-2 h-4 w-4" />
                <span>All Collections</span>
                {selectedCollectionId === null && (
                  <Check className="ml-auto h-4 w-4" />
                )}
              </CommandItem>

              {/* Collection list */}
              {collections.map((collection) => (
                <CommandItem
                  key={collection.id}
                  value={collection.name}
                  onSelect={() => {
                    setSelectedCollectionId(collection.id);
                    setOpen(false);
                  }}
                >
                  <span className="truncate">{collection.name}</span>
                  {collection.artifact_count > 0 && (
                    <span className="ml-auto text-xs text-muted-foreground">
                      {collection.artifact_count}
                    </span>
                  )}
                  {selectedCollectionId === collection.id && (
                    <Check className="ml-2 h-4 w-4" />
                  )}
                </CommandItem>
              ))}
            </CommandGroup>

            {/* Add Collection option */}
            {onCreateCollection && (
              <>
                <CommandSeparator />
                <CommandGroup>
                  <CommandItem
                    onSelect={() => {
                      setOpen(false);
                      onCreateCollection();
                    }}
                  >
                    <FolderPlus className="mr-2 h-4 w-4" />
                    <span>Add Collection</span>
                  </CommandItem>
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
