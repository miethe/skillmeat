'use client';

import { useState } from 'react';
import { CollectionSwitcher } from './collection-switcher';
import { CreateCollectionDialog } from './create-collection-dialog';

interface CollectionSwitcherWithDialogsProps {
  /** Additional CSS classes for the switcher button */
  className?: string;
}

/**
 * CollectionSwitcherWithDialogs - Wrapper component that combines CollectionSwitcher with CreateCollectionDialog
 *
 * This component manages the state for the create dialog and wires up the CollectionSwitcher's
 * "Add Collection" action to trigger the dialog.
 *
 * Usage:
 * ```tsx
 * <CollectionSwitcherWithDialogs className="w-[250px]" />
 * ```
 *
 * This is a convenience component that can be used in the navigation sidebar or anywhere
 * you want a collection switcher with full create functionality.
 */
export function CollectionSwitcherWithDialogs({ className }: CollectionSwitcherWithDialogsProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);

  return (
    <>
      <CollectionSwitcher
        onCreateCollection={() => setShowCreateDialog(true)}
        className={className}
      />

      <CreateCollectionDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={(collectionId) => {
          console.log('Collection created:', collectionId);
        }}
      />
    </>
  );
}
