# History Components

Components for version snapshot management.

## RollbackDialog

Multi-step confirmation dialog for rolling back collection to a previous snapshot.

### Features

- **Safety Analysis**: Auto-fetches and displays rollback safety analysis
- **Conflict Detection**: Shows files with conflicts and files safe to restore
- **Preserve Changes**: Option to preserve uncommitted changes via 3-way merge
- **Result Display**: Shows detailed results after rollback (files merged, restored, conflicts)
- **Safety Snapshot**: Creates safety snapshot before rollback

### Usage

```tsx
import { RollbackDialog } from '@/components/history';
import { useState } from 'react';

function SnapshotView() {
  const [showRollback, setShowRollback] = useState(false);
  const [selectedSnapshot, setSelectedSnapshot] = useState<string | null>(null);

  const handleRollbackSuccess = (result: RollbackResponse) => {
    console.log('Rollback complete:', result);
    // Refresh snapshot list, show success toast, etc.
  };

  return (
    <>
      <button
        onClick={() => {
          setSelectedSnapshot('snapshot-id-here');
          setShowRollback(true);
        }}
      >
        Rollback
      </button>

      {selectedSnapshot && (
        <RollbackDialog
          snapshotId={selectedSnapshot}
          collectionName="default"
          open={showRollback}
          onOpenChange={setShowRollback}
          onSuccess={handleRollbackSuccess}
        />
      )}
    </>
  );
}
```

### Props

```typescript
interface RollbackDialogProps {
  snapshotId: string; // Snapshot SHA-256 hash identifier
  collectionName?: string; // Optional collection name
  open: boolean; // Dialog open state
  onOpenChange: (open: boolean) => void; // Dialog state change handler
  onSuccess?: (result: RollbackResponse) => void; // Success callback
}
```

### Dialog Flow

1. **Snapshot Info**: Displays snapshot message, timestamp, and artifact count
2. **Safety Analysis**: Auto-fetches and shows:
   - Safety status badge (green/red/yellow)
   - Files with conflicts (with warning icons)
   - Files safe to restore (with check icons)
   - Any warnings
3. **Confirmation**: User must check:
   - "I understand this will restore files" (required)
   - "Preserve local changes" (optional, default: true)
4. **Execution**: Rollback button disabled until confirmed
5. **Results**: After rollback, shows:
   - Files merged count
   - Files restored count
   - Any conflicts requiring manual resolution
   - Safety snapshot ID (if created)

### Dependencies

- Hooks: `@/hooks/use-snapshots` (useRollbackAnalysis, useRollback, useSnapshot)
- Types: `@/types/snapshot` (RollbackResponse, etc.)
- UI: shadcn/ui components (Dialog, Button, Checkbox, Alert, Badge, ScrollArea, Label)

### Related

- Backend API: `/api/v1/versions/snapshots/{id}/rollback` (POST)
- Phase: 8 (Versioning & Merge System PRD)
