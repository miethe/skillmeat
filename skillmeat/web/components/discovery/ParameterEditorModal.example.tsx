/**
 * Example Usage: ParameterEditorModal
 *
 * Demonstrates how to use the ParameterEditorModal component
 * to edit artifact parameters.
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ParameterEditorModal, ArtifactParameters } from './ParameterEditorModal';
import type { Artifact } from '@/types/artifact';

export function ParameterEditorModalExample() {
  const [isOpen, setIsOpen] = useState(false);

  // Example artifact
  const artifact: Artifact = {
    id: '1',
    name: 'example-skill',
    type: 'skill',
    scope: 'user',
    status: 'active',
    source: 'user/repo/skills/example',
    version: 'v1.0.0',
    tags: ['development', 'testing'],
    aliases: ['ex', 'example'],
    metadata: {
      title: 'Example Skill',
      description: 'An example skill for testing',
    },
    upstreamStatus: {
      hasUpstream: true,
      isOutdated: false,
    },
    usageStats: {
      totalDeployments: 0,
      activeProjects: 0,
      usageCount: 0,
    },
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };

  const handleSave = async (parameters: ArtifactParameters) => {
    console.log('Saving parameters:', parameters);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1000));

    // In a real implementation, you would:
    // 1. Call API to update artifact parameters
    // 2. Invalidate React Query cache
    // 3. Show success toast
    //
    // Example:
    // const response = await updateArtifact(artifact.id, parameters);
    // queryClient.invalidateQueries(['artifacts']);
  };

  return (
    <div className="space-y-4 p-4">
      <h2 className="text-2xl font-bold">Parameter Editor Modal Example</h2>

      <div className="space-y-2">
        <p className="text-sm text-muted-foreground">
          Click the button below to open the parameter editor modal and modify artifact settings.
        </p>

        <Button onClick={() => setIsOpen(true)}>Edit Parameters</Button>
      </div>

      <ParameterEditorModal
        artifact={artifact}
        open={isOpen}
        onClose={() => setIsOpen(false)}
        onSave={handleSave}
      />

      <div className="rounded-lg border p-4">
        <h3 className="mb-2 font-semibold">Current Artifact Parameters:</h3>
        <pre className="text-xs">
          {JSON.stringify(
            {
              source: artifact.source,
              version: artifact.version,
              scope: artifact.scope,
              tags: artifact.tags,
              aliases: artifact.aliases,
            },
            null,
            2
          )}
        </pre>
      </div>
    </div>
  );
}

/**
 * Usage in Bulk Import Modal:
 *
 * ```tsx
 * import { ParameterEditorModal, ArtifactParameters } from '@/components/discovery';
 *
 * export function BulkImportModal({ artifacts, open, onClose, onImport }) {
 *   const [editingArtifact, setEditingArtifact] = useState<DiscoveredArtifact | null>(null);
 *   const [artifactsToImport, setArtifactsToImport] = useState(artifacts);
 *
 *   const handleParametersSaved = async (parameters: ArtifactParameters) => {
 *     // Update the artifact in the list
 *     setArtifactsToImport(prev =>
 *       prev.map(artifact =>
 *         artifact.name === editingArtifact?.name
 *           ? { ...artifact, ...parameters }
 *           : artifact
 *       )
 *     );
 *   };
 *
 *   return (
 *     <>
 *       <Dialog open={open} onOpenChange={onClose}>
 *         {artifacts.map(artifact => (
 *           <div key={artifact.name}>
 *             <span>{artifact.name}</span>
 *             <Button onClick={() => setEditingArtifact(artifact)}>
 *               Edit Parameters
 *             </Button>
 *           </div>
 *         ))}
 *       </Dialog>
 *
 *       {editingArtifact && (
 *         <ParameterEditorModal
 *           artifact={editingArtifact}
 *           open={!!editingArtifact}
 *           onClose={() => setEditingArtifact(null)}
 *           onSave={handleParametersSaved}
 *         />
 *       )}
 *     </>
 *   );
 * }
 * ```
 */

/**
 * Usage in Collection Page:
 *
 * ```tsx
 * import { ParameterEditorModal, ArtifactParameters } from '@/components/discovery';
 * import { useUpdateArtifact } from '@/hooks';
 *
 * export function CollectionPage() {
 *   const [editingArtifact, setEditingArtifact] = useState<Artifact | null>(null);
 *   const updateArtifact = useUpdateArtifact();
 *
 *   const handleParametersSaved = async (parameters: ArtifactParameters) => {
 *     if (!editingArtifact) return;
 *
 *     await updateArtifact.mutateAsync({
 *       id: editingArtifact.id,
 *       ...parameters,
 *     });
 *   };
 *
 *   return (
 *     <>
 *       {artifacts.map(artifact => (
 *         <ArtifactCard
 *           key={artifact.id}
 *           artifact={artifact}
 *           onEdit={() => setEditingArtifact(artifact)}
 *         />
 *       ))}
 *
 *       {editingArtifact && (
 *         <ParameterEditorModal
 *           artifact={editingArtifact}
 *           open={!!editingArtifact}
 *           onClose={() => setEditingArtifact(null)}
 *           onSave={handleParametersSaved}
 *         />
 *       )}
 *     </>
 *   );
 * }
 * ```
 */
