/**
 * Example usage of DiffViewer with sync resolution actions
 *
 * This demonstrates the new sync conflict resolution features added in Phase 5.
 */
'use client';

import { useState } from 'react';
import { DiffViewer, type ResolutionType } from './diff-viewer';
import type { FileDiff } from '@/sdk/models/FileDiff';

const exampleDiffs: FileDiff[] = [
  {
    file_path: 'skills/canvas-design/skill.md',
    status: 'modified',
    unified_diff: `@@ -1,5 +1,5 @@
 # Canvas Design Skill

-Version: 1.0.0
+Version: 1.1.0

 A skill for designing canvas layouts.`,
  },
  {
    file_path: 'skills/canvas-design/config.json',
    status: 'modified',
    unified_diff: `@@ -1,4 +1,4 @@
 {
-  "enabled": false,
+  "enabled": true,
   "author": "skillmeat"
 }`,
  },
  {
    file_path: 'skills/canvas-design/new-feature.js',
    status: 'added',
    unified_diff: null,
  },
];

/**
 * Example 1: Basic diff viewer without resolution actions
 */
export function BasicDiffViewerExample() {
  return (
    <div className="h-96 border rounded">
      <DiffViewer
        files={exampleDiffs}
        leftLabel="Collection"
        rightLabel="Project"
      />
    </div>
  );
}

/**
 * Example 2: Diff viewer with sync resolution actions
 */
export function SyncResolutionExample() {
  const [isResolving, setIsResolving] = useState(false);
  const [resolvedWith, setResolvedWith] = useState<ResolutionType | null>(null);

  const handleResolve = async (resolution: ResolutionType) => {
    console.log('Resolving conflict with:', resolution);
    setIsResolving(true);

    // Simulate async resolution
    await new Promise((resolve) => setTimeout(resolve, 2000));

    setIsResolving(false);
    setResolvedWith(resolution);

    // In real implementation, this would:
    // - Call backend API to apply resolution
    // - Update artifact content
    // - Refresh diff view or close dialog
  };

  return (
    <div className="space-y-4">
      <div className="h-96 border rounded">
        <DiffViewer
          files={exampleDiffs}
          leftLabel="Collection"
          rightLabel="Project (Deployed)"
          showResolutionActions={true}
          onResolve={handleResolve}
          localLabel="Project"
          remoteLabel="Collection"
          previewMode={true}
          isResolving={isResolving}
        />
      </div>

      {resolvedWith && (
        <div className="p-4 bg-green-100 dark:bg-green-900 rounded">
          <p>✅ Conflict resolved using: <strong>{resolvedWith}</strong></p>
        </div>
      )}
    </div>
  );
}

/**
 * Example 3: Custom labels
 */
export function CustomLabelsExample() {
  const [isResolving, setIsResolving] = useState(false);

  const handleResolve = async (resolution: ResolutionType) => {
    setIsResolving(true);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsResolving(false);
    alert(`Resolved with: ${resolution}`);
  };

  return (
    <div className="h-96 border rounded">
      <DiffViewer
        files={exampleDiffs}
        leftLabel="Upstream (GitHub)"
        rightLabel="Working Copy"
        showResolutionActions={true}
        onResolve={handleResolve}
        localLabel="Working Copy"
        remoteLabel="Upstream"
        isResolving={isResolving}
      />
    </div>
  );
}

/**
 * Example 4: Preview mode disabled
 */
export function NoPreviewExample() {
  const handleResolve = (resolution: ResolutionType) => {
    console.log('Immediate resolution:', resolution);
    // Apply resolution immediately without preview
  };

  return (
    <div className="h-96 border rounded">
      <DiffViewer
        files={exampleDiffs}
        leftLabel="Collection"
        rightLabel="Project"
        showResolutionActions={true}
        onResolve={handleResolve}
        previewMode={false}  // No preview message
      />
    </div>
  );
}

/**
 * Demo page showing all examples
 */
export default function DiffViewerExamplesPage() {
  return (
    <div className="container mx-auto py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold mb-2">DiffViewer Examples</h1>
        <p className="text-muted-foreground">
          Demonstrating sync conflict resolution features added in Phase 5
        </p>
      </div>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold mb-2">Basic Diff Viewer</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Traditional diff view without resolution actions
          </p>
        </div>
        <BasicDiffViewerExample />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold mb-2">Sync Resolution Actions</h2>
          <p className="text-sm text-muted-foreground mb-4">
            With resolution buttons, preview mode, and loading states
          </p>
        </div>
        <SyncResolutionExample />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold mb-2">Custom Labels</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Using custom labels for different sync scenarios
          </p>
        </div>
        <CustomLabelsExample />
      </section>

      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold mb-2">No Preview Mode</h2>
          <p className="text-sm text-muted-foreground mb-4">
            Resolution actions without preview message
          </p>
        </div>
        <NoPreviewExample />
      </section>
    </div>
  );
}
