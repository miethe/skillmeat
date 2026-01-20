/**
 * Example Usage: BulkImportModal
 *
 * This file demonstrates how to use the BulkImportModal component
 */

'use client';

import { useState } from 'react';
import { BulkImportModal, DiscoveredArtifact } from './BulkImportModal';
import { Button } from '@/components/ui/button';

export function BulkImportModalExample() {
  const [modalOpen, setModalOpen] = useState(false);

  // Example discovered artifacts
  const mockArtifacts: DiscoveredArtifact[] = [
    {
      type: 'skill',
      name: 'document-analyzer',
      source: 'local/.claude/skills/document-analyzer',
      version: '1.2.0',
      scope: 'user',
      tags: ['document', 'analysis'],
      description: 'Analyzes document structure and content',
      path: '/home/user/.claude/skills/document-analyzer',
      discovered_at: '2024-11-30T10:00:00Z',
    },
    {
      type: 'command',
      name: 'git-helper',
      source: 'local/.claude/commands/git-helper',
      version: '2.0.1',
      scope: 'local',
      tags: ['git', 'version-control'],
      description: 'Git workflow automation',
      path: '/home/user/project/.claude/commands/git-helper',
      discovered_at: '2024-11-30T10:05:00Z',
    },
    {
      type: 'agent',
      name: 'code-reviewer',
      source: 'local/.claude/agents/code-reviewer',
      version: '0.9.0',
      tags: ['code', 'review', 'quality'],
      path: '/home/user/.claude/agents/code-reviewer',
      discovered_at: '2024-11-30T10:10:00Z',
    },
  ];

  const handleImport = async (selected: DiscoveredArtifact[]) => {
    console.log('Importing artifacts:', selected);

    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 2000));

    // In real usage, you would call your API here:
    // const response = await fetch('/api/artifacts/import', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ artifacts: selected }),
    // });
    //
    // if (!response.ok) {
    //   throw new Error('Import failed');
    // }
  };

  return (
    <div className="p-6">
      <h2 className="mb-4 text-2xl font-bold">Bulk Import Modal Example</h2>

      <Button onClick={() => setModalOpen(true)}>
        Review Discovered Artifacts ({mockArtifacts.length})
      </Button>

      <BulkImportModal
        artifacts={mockArtifacts}
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onImport={handleImport}
      />

      <div className="mt-6 rounded-lg bg-muted p-4">
        <h3 className="mb-2 font-semibold">Usage:</h3>
        <pre className="overflow-auto text-xs">
          {`<BulkImportModal
  artifacts={discoveredArtifacts}
  open={isOpen}
  onClose={() => setIsOpen(false)}
  onImport={async (selected) => {
    // Handle import logic
    await importArtifacts(selected);
  }}
/>`}
        </pre>
      </div>
    </div>
  );
}
