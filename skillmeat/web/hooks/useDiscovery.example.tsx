/**
 * Example usage of discovery hooks
 *
 * This file demonstrates how to use the useDiscovery, useGitHubMetadata,
 * and useEditArtifactParameters hooks in React components.
 *
 * NOTE: This is an example file and not part of the production code.
 */

import React from 'react';
import { useDiscovery, useGitHubMetadata, useEditArtifactParameters } from './useDiscovery';
import type { BulkImportArtifact } from '@/types/discovery';

/**
 * Example: Discovery and bulk import
 */
export function DiscoveryExample() {
  const {
    discoveredArtifacts,
    discoveredCount,
    scanErrors,
    isDiscovering,
    discoverError,
    refetchDiscovery,
    bulkImport,
    isImporting,
    importResult,
  } = useDiscovery();

  const handleDiscover = async () => {
    await refetchDiscovery();
  };

  const handleBulkImport = async () => {
    const artifactsToImport: BulkImportArtifact[] = discoveredArtifacts.map((artifact) => ({
      source: artifact.source || artifact.path,
      artifact_type: artifact.type,
      name: artifact.name,
      description: artifact.description,
      tags: artifact.tags,
      scope: artifact.scope,
    }));

    const result = await bulkImport({
      artifacts: artifactsToImport,
      auto_resolve_conflicts: false,
    });

    console.log('Import result:', result);
  };

  return (
    <div>
      <h2>Artifact Discovery</h2>

      <button onClick={handleDiscover} disabled={isDiscovering}>
        {isDiscovering ? 'Scanning...' : 'Scan for Artifacts'}
      </button>

      {discoverError && <div>Error: {discoverError.message}</div>}

      {discoveredCount > 0 && (
        <div>
          <p>Found {discoveredCount} artifacts</p>
          {scanErrors.length > 0 && <p>Errors: {scanErrors.join(', ')}</p>}

          <ul>
            {discoveredArtifacts.map((artifact, index) => (
              <li key={index}>
                {artifact.name} ({artifact.type}) - {artifact.path}
              </li>
            ))}
          </ul>

          <button onClick={handleBulkImport} disabled={isImporting}>
            {isImporting ? 'Importing...' : 'Import All'}
          </button>
        </div>
      )}

      {importResult && (
        <div>
          <p>
            Imported {importResult.total_imported} of {importResult.total_requested} artifacts
          </p>
          {importResult.total_failed > 0 && <p>Failed: {importResult.total_failed}</p>}
        </div>
      )}
    </div>
  );
}

/**
 * Example: GitHub metadata fetch
 */
export function GitHubMetadataExample() {
  const { mutate: fetchMetadata, isPending, data, error } = useGitHubMetadata();
  const [source, setSource] = React.useState('anthropics/skills/canvas-design');

  const handleFetch = () => {
    fetchMetadata(source);
  };

  return (
    <div>
      <h2>GitHub Metadata</h2>

      <input type="text" value={source} onChange={(e) => setSource(e.target.value)} />

      <button onClick={handleFetch} disabled={isPending}>
        {isPending ? 'Fetching...' : 'Fetch Metadata'}
      </button>

      {error && <div>Error: {error.message}</div>}

      {data && (
        <div>
          <h3>{data.title || 'No title'}</h3>
          <p>{data.description}</p>
          <p>Author: {data.author}</p>
          <p>License: {data.license}</p>
          <p>Topics: {data.topics.join(', ')}</p>
          <p>URL: {data.url}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Example: Edit artifact parameters
 */
export function EditParametersExample({ artifactId }: { artifactId: string }) {
  const { mutate: updateParameters, isPending, data, error } = useEditArtifactParameters();

  const handleUpdate = () => {
    updateParameters({
      artifactId,
      parameters: {
        tags: ['updated', 'modified'],
        aliases: ['new-alias'],
        scope: 'user',
      },
    });
  };

  return (
    <div>
      <h2>Edit Parameters</h2>

      <button onClick={handleUpdate} disabled={isPending}>
        {isPending ? 'Updating...' : 'Update Parameters'}
      </button>

      {error && <div>Error: {error.message}</div>}

      {data && (
        <div>
          <p>Success: {data.message}</p>
          <p>Updated fields: {data.updated_fields.join(', ')}</p>
        </div>
      )}
    </div>
  );
}

/**
 * Example: Combined usage in a full component
 */
export function DiscoveryDashboard() {
  const discovery = useDiscovery();
  const githubMetadata = useGitHubMetadata();
  const editParameters = useEditArtifactParameters();

  // Example: Discover artifacts, fetch metadata for the first one, and update its parameters
  const handleFullWorkflow = async () => {
    // Step 1: Discover artifacts
    const discoverResult = await discovery.refetchDiscovery();

    if (discoverResult.data && discoverResult.data.artifacts.length > 0) {
      const firstArtifact = discoverResult.data.artifacts[0];

      // Step 2: Fetch GitHub metadata if source is available
      if (firstArtifact.source) {
        const metadata = await githubMetadata.mutateAsync(firstArtifact.source);

        // Step 3: Update parameters with fetched metadata
        if (metadata) {
          await editParameters.mutateAsync({
            artifactId: firstArtifact.name,
            parameters: {
              tags: metadata.topics,
            },
          });
        }
      }
    }
  };

  return (
    <div>
      <h1>Discovery Dashboard</h1>
      <button onClick={handleFullWorkflow}>Run Full Workflow</button>

      <DiscoveryExample />
      <GitHubMetadataExample />
    </div>
  );
}
