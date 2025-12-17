/**
 * Example usage of VersionComparisonView component
 *
 * This file demonstrates how to use the version comparison component
 * in different scenarios.
 */

import { VersionComparisonView } from './version-comparison-view';

/**
 * Example 1: Basic comparison between two snapshots
 */
export function BasicComparisonExample() {
  return (
    <VersionComparisonView
      snapshotId1="abc123def456..." // Older snapshot
      snapshotId2="def456ghi789..." // Newer snapshot
      collectionName="default"
      onClose={() => console.log('Comparison closed')}
    />
  );
}

/**
 * Example 2: Comparison in a dialog/modal
 */
export function DialogComparisonExample() {
  const handleClose = () => {
    // Close dialog logic
    console.log('Closing comparison dialog');
  };

  return (
    <div className="mx-auto max-w-4xl p-4">
      <VersionComparisonView
        snapshotId1="abc123..."
        snapshotId2="def456..."
        onClose={handleClose}
      />
    </div>
  );
}

/**
 * Example 3: Comparison with custom styling
 */
export function StyledComparisonExample() {
  return (
    <VersionComparisonView
      snapshotId1="abc123..."
      snapshotId2="def456..."
      collectionName="my-collection"
      className="border-2 border-primary shadow-lg"
    />
  );
}

/**
 * Example 4: Full page comparison view
 */
export function FullPageComparisonExample() {
  return (
    <div className="container mx-auto py-6">
      <h1 className="mb-6 text-3xl font-bold">Snapshot Comparison</h1>
      <VersionComparisonView
        snapshotId1="old-snapshot-id"
        snapshotId2="new-snapshot-id"
        collectionName="default"
      />
    </div>
  );
}

/**
 * Example 5: Interactive comparison from history list
 */
export function InteractiveComparisonExample() {
  const snapshots = [
    { id: 'snapshot1', timestamp: '2025-12-17T10:00:00Z', message: 'Initial version' },
    { id: 'snapshot2', timestamp: '2025-12-17T11:00:00Z', message: 'Added features' },
    { id: 'snapshot3', timestamp: '2025-12-17T12:00:00Z', message: 'Bug fixes' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="mb-4 text-xl font-semibold">Select Snapshots to Compare</h2>
        {/* Snapshot selection UI would go here */}
      </div>

      <VersionComparisonView
        snapshotId1={snapshots[0].id}
        snapshotId2={snapshots[2].id}
        collectionName="default"
      />
    </div>
  );
}

/**
 * Example 6: Comparison with state management
 */
export function StatefulComparisonExample() {
  // In a real component, you'd use useState
  const showComparison = true;
  const selectedSnapshot1 = 'abc123...';
  const selectedSnapshot2 = 'def456...';

  const handleClose = () => {
    // setState to hide comparison
    console.log('Hiding comparison');
  };

  if (!showComparison) {
    return null;
  }

  return (
    <VersionComparisonView
      snapshotId1={selectedSnapshot1}
      snapshotId2={selectedSnapshot2}
      onClose={handleClose}
    />
  );
}
