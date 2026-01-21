/**
 * SkipPreferencesList Component - Usage Examples
 *
 * This file demonstrates how to use the SkipPreferencesList component
 * in the Discovery Tab and other contexts.
 */

'use client';

import { useState, useEffect } from 'react';
import { SkipPreferencesList } from './SkipPreferencesList';
import {
  loadSkipPrefs,
  saveSkipPrefs,
  removeSkipPref,
  clearSkipPrefs,
  buildArtifactKey,
} from '@/lib/skip-preferences';
import type { SkipPreference } from '@/types/discovery';

/**
 * Example 1: Basic usage with localStorage persistence
 */
export function BasicExample() {
  const [skipPrefs, setSkipPrefs] = useState<SkipPreference[]>([]);
  const projectId = 'my-project-123'; // Get from context or props

  useEffect(() => {
    // Load preferences on mount
    const prefs = loadSkipPrefs(projectId);
    setSkipPrefs(prefs);
  }, [projectId]);

  const handleRemoveSkip = (artifactKey: string) => {
    const success = removeSkipPref(projectId, artifactKey);
    if (success) {
      // Reload preferences
      setSkipPrefs(loadSkipPrefs(projectId));
    }
  };

  const handleClearAll = () => {
    clearSkipPrefs(projectId);
    setSkipPrefs([]);
  };

  return (
    <div className="space-y-4">
      <h2>Skip Preferences Management</h2>
      <SkipPreferencesList
        skipPrefs={skipPrefs}
        onRemoveSkip={handleRemoveSkip}
        onClearAll={handleClearAll}
      />
    </div>
  );
}

/**
 * Example 2: Integrated with Discovery Tab
 */
export function DiscoveryTabExample() {
  const [skipPrefs, setSkipPrefs] = useState<SkipPreference[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const projectId = 'my-project-123';

  // Load skip preferences
  useEffect(() => {
    const prefs = loadSkipPrefs(projectId);
    setSkipPrefs(prefs);
  }, [projectId]);

  const handleRemoveSkip = async (artifactKey: string) => {
    setIsLoading(true);
    try {
      const success = removeSkipPref(projectId, artifactKey);
      if (success) {
        // Reload preferences
        const updated = loadSkipPrefs(projectId);
        setSkipPrefs(updated);

        // Optionally trigger a re-scan to show the artifact
        // await triggerDiscoveryScan();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearAll = async () => {
    setIsLoading(true);
    try {
      clearSkipPrefs(projectId);
      setSkipPrefs([]);

      // Optionally trigger a re-scan to show all artifacts
      // await triggerDiscoveryScan();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto space-y-6 py-6">
      <h1 className="text-3xl font-bold">Discovery</h1>

      {/* Discovery scan results would go here */}
      <div className="rounded-lg border p-4">
        <p>Discovery scan results...</p>
      </div>

      {/* Skip Preferences List */}
      <SkipPreferencesList
        skipPrefs={skipPrefs}
        onRemoveSkip={handleRemoveSkip}
        onClearAll={handleClearAll}
        isLoading={isLoading}
      />
    </div>
  );
}

/**
 * Example 3: With custom notification/toast on actions
 */
export function WithNotificationExample() {
  const [skipPrefs, setSkipPrefs] = useState<SkipPreference[]>([]);
  const projectId = 'my-project-123';

  // Mock toast function - replace with your actual toast implementation
  const showToast = (message: string, type: 'success' | 'error') => {
    console.log(`[${type}] ${message}`);
  };

  useEffect(() => {
    const prefs = loadSkipPrefs(projectId);
    setSkipPrefs(prefs);
  }, [projectId]);

  const handleRemoveSkip = (artifactKey: string) => {
    const success = removeSkipPref(projectId, artifactKey);
    if (success) {
      const updated = loadSkipPrefs(projectId);
      setSkipPrefs(updated);
      showToast('Artifact un-skipped successfully', 'success');
    } else {
      showToast('Failed to un-skip artifact', 'error');
    }
  };

  const handleClearAll = () => {
    const count = skipPrefs.length;
    clearSkipPrefs(projectId);
    setSkipPrefs([]);
    showToast(`Cleared ${count} skip preference${count !== 1 ? 's' : ''}`, 'success');
  };

  return (
    <SkipPreferencesList
      skipPrefs={skipPrefs}
      onRemoveSkip={handleRemoveSkip}
      onClearAll={handleClearAll}
    />
  );
}

/**
 * Example 4: Building skip list from discovery results
 */
export function WithDiscoveryResultsExample() {
  const [skipPrefs, setSkipPrefs] = useState<SkipPreference[]>([]);
  const [discoveredArtifacts, setDiscoveredArtifacts] = useState<any[]>([]);
  const projectId = 'my-project-123';

  // Add artifact to skip list
  const handleSkipArtifact = (artifact: any, reason: string) => {
    const artifactKey = buildArtifactKey(artifact.type, artifact.name);
    const current = loadSkipPrefs(projectId);

    if (!current.some((p) => p.artifact_key === artifactKey)) {
      const newPref: SkipPreference = {
        artifact_key: artifactKey,
        skip_reason: reason,
        added_date: new Date().toISOString(),
      };
      current.push(newPref);
      saveSkipPrefs(projectId, current);
      setSkipPrefs(current);
    }
  };

  const handleRemoveSkip = (artifactKey: string) => {
    const success = removeSkipPref(projectId, artifactKey);
    if (success) {
      setSkipPrefs(loadSkipPrefs(projectId));
    }
  };

  const handleClearAll = () => {
    clearSkipPrefs(projectId);
    setSkipPrefs([]);
  };

  return (
    <div className="space-y-4">
      {/* Discovery results with skip actions */}
      <div className="rounded-lg border p-4">
        {discoveredArtifacts.map((artifact) => (
          <div key={artifact.name} className="flex items-center justify-between p-2">
            <span>{artifact.name}</span>
            <button
              onClick={() => handleSkipArtifact(artifact, 'User chose to skip during discovery')}
            >
              Skip
            </button>
          </div>
        ))}
      </div>

      {/* Skip Preferences Management */}
      <SkipPreferencesList
        skipPrefs={skipPrefs}
        onRemoveSkip={handleRemoveSkip}
        onClearAll={handleClearAll}
      />
    </div>
  );
}

/**
 * Example 5: Read-only view (no actions)
 */
export function ReadOnlyExample() {
  const [skipPrefs, setSkipPrefs] = useState<SkipPreference[]>([]);
  const projectId = 'my-project-123';

  useEffect(() => {
    const prefs = loadSkipPrefs(projectId);
    setSkipPrefs(prefs);
  }, [projectId]);

  // Empty handlers for read-only mode
  const noOp = () => {
    console.log('Read-only mode - no actions allowed');
  };

  return (
    <SkipPreferencesList
      skipPrefs={skipPrefs}
      onRemoveSkip={noOp}
      onClearAll={noOp}
      isLoading={false}
    />
  );
}
