/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MergeWorkflow } from '@/components/entity/merge-workflow';
import type { ArtifactDiffResponse } from '@/sdk';

// Mock the API
jest.mock('@/lib/api', () => ({
  apiRequest: jest.fn(),
}));

const mockDiffResponse: ArtifactDiffResponse = {
  artifact_id: 'skill:test',
  has_changes: true,
  summary: {
    added: 1,
    modified: 2,
    deleted: 0,
    unchanged: 5,
  },
  files: [
    {
      file_path: 'src/new.ts',
      status: 'added',
      unified_diff: null,
    },
    {
      file_path: 'src/modified.ts',
      status: 'modified',
      unified_diff: `@@ -1,3 +1,3 @@
 function test() {
-  return 'old';
+  return 'new';
 }`,
    },
    {
      file_path: 'src/changed.ts',
      status: 'modified',
      unified_diff: `@@ -1,2 +1,2 @@
-const a = 1;
+const a = 2;`,
    },
  ],
};

const mockEmptyDiffResponse: ArtifactDiffResponse = {
  artifact_id: 'skill:test',
  has_changes: false,
  summary: {
    added: 0,
    modified: 0,
    deleted: 0,
    unchanged: 5,
  },
  files: [],
};

describe('MergeWorkflow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiRequest } = require('@/lib/api');
    apiRequest.mockResolvedValue(mockDiffResponse);
  });

  it('renders loading state initially', () => {
    render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/test/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />
    );

    expect(screen.getByRole('progressbar', { hidden: true })).toBeInTheDocument();
  });

  it('loads diff data on mount', async () => {
    const { apiRequest } = require('@/lib/api');

    render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/test/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledWith(
        expect.stringContaining('/artifacts/skill:test/diff')
      );
    });
  });

  it('displays error when diff loading fails', async () => {
    const { apiRequest } = require('@/lib/api');
    apiRequest.mockRejectedValue(new Error('Failed to load'));

    render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/test/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Failed to load diff')).toBeInTheDocument();
      expect(screen.getByText('Failed to load')).toBeInTheDocument();
    });
  });

  describe('Step Indicators', () => {
    it('renders all three step indicators', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Preview')).toBeInTheDocument();
        expect(screen.getByText('Resolve')).toBeInTheDocument();
        expect(screen.getByText('Apply')).toBeInTheDocument();
      });
    });

    it('shows Preview step as active initially', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        const previewStep = screen.getByText('Preview');
        expect(previewStep.previousSibling).toHaveClass('border-primary');
      });
    });
  });

  describe('Preview Step', () => {
    it('displays summary of changes', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Preview Changes')).toBeInTheDocument();
        expect(screen.getByText('+1 added')).toBeInTheDocument();
        expect(screen.getByText('~2 modified')).toBeInTheDocument();
      });
    });

    it('shows conflict warning when conflicts detected', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Conflicts Detected')).toBeInTheDocument();
      });
    });

    it('shows correct direction description for upstream', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(
          screen.getByText(/Review changes to sync from project to collection/)
        ).toBeInTheDocument();
      });
    });

    it('shows correct direction description for downstream', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="downstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        expect(
          screen.getByText(/Review changes to sync from collection to project/)
        ).toBeInTheDocument();
      });
    });

    it('disables Continue button when no changes', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockEmptyDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        const continueButton = screen.getByRole('button', { name: /Continue/ });
        expect(continueButton).toBeDisabled();
      });
    });

    it('calls onCancel when Cancel button clicked', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);
      const handleCancel = jest.fn();

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={handleCancel}
        />
      );

      await waitFor(() => {
        const cancelButton = screen.getByRole('button', { name: /Cancel/ });
        fireEvent.click(cancelButton);
      });

      expect(handleCancel).toHaveBeenCalled();
    });

    it('progresses to Resolve step when Continue clicked with conflicts', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        const continueButton = screen.getByRole('button', { name: /Continue/ });
        fireEvent.click(continueButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Resolve Conflicts')).toBeInTheDocument();
      });
    });

    it('skips to Apply step when no conflicts', async () => {
      const noConflictDiff = {
        ...mockDiffResponse,
        files: [
          {
            file_path: 'src/new.ts',
            status: 'added' as const,
            unified_diff: null,
          },
        ],
      };
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(noConflictDiff);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        const continueButton = screen.getByRole('button', { name: /Continue/ });
        fireEvent.click(continueButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Apply Changes')).toBeInTheDocument();
      });
    });
  });

  describe('Resolve Step', () => {
    it('displays conflict resolution options for each modified file', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        const continueButton = screen.getByRole('button', { name: /Continue/ });
        fireEvent.click(continueButton);
      });

      await waitFor(() => {
        expect(screen.getByText('src/modified.ts')).toBeInTheDocument();
        expect(screen.getByText('src/changed.ts')).toBeInTheDocument();
      });
    });

    it('enables Continue button when all conflicts resolved', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      await waitFor(() => {
        const continueButton = screen.getByRole('button', { name: /Continue/ });
        fireEvent.click(continueButton);
      });

      await waitFor(() => {
        // Default resolution should be set, so Continue should be enabled
        const resolveButton = screen.getByRole('button', { name: /Continue/ });
        expect(resolveButton).not.toBeDisabled();
      });
    });

    it('navigates back to Preview when Back clicked', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      // Go to Resolve step
      await waitFor(() => {
        const continueButton = screen.getByRole('button', { name: /Continue/ });
        fireEvent.click(continueButton);
      });

      // Click Back
      await waitFor(() => {
        const backButton = screen.getByRole('button', { name: /Back/ });
        fireEvent.click(backButton);
      });

      await waitFor(() => {
        expect(screen.getByText('Preview Changes')).toBeInTheDocument();
      });
    });
  });

  describe('Apply Step', () => {
    it('displays summary before applying', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      // Navigate to Apply step
      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      await waitFor(() => {
        expect(screen.getByText('Apply Changes')).toBeInTheDocument();
        expect(screen.getByText(/Files to add:/)).toBeInTheDocument();
        expect(screen.getByText(/Files to modify:/)).toBeInTheDocument();
      });
    });

    it('shows progress indicator when applying changes', async () => {
      const { apiRequest } = require('@/lib/api');
      apiRequest.mockResolvedValue(mockDiffResponse);
      apiRequest.mockResolvedValueOnce(mockDiffResponse); // For initial load
      apiRequest.mockResolvedValueOnce({
        success: true,
        message: 'Sync completed',
      }); // For sync

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      // Navigate to Apply step
      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      // Click Apply Changes
      await waitFor(() => {
        const applyButton = screen.getByRole('button', { name: /Apply Changes/ });
        fireEvent.click(applyButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/Applying changes.../)).toBeInTheDocument();
      });
    });

    it('displays success message on completion', async () => {
      const { apiRequest } = require('@/lib/api');
      const syncResponse = {
        success: true,
        message: 'Successfully synced 3 files',
        synced_files_count: 3,
      };

      apiRequest.mockResolvedValueOnce(mockDiffResponse);
      apiRequest.mockResolvedValueOnce(syncResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={jest.fn()}
          onCancel={jest.fn()}
        />
      );

      // Navigate through steps
      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Apply Changes/ }));
      });

      await waitFor(() => {
        expect(screen.getByText('Successfully synced 3 files')).toBeInTheDocument();
      });
    });

    it('calls onComplete after successful sync', async () => {
      const { apiRequest } = require('@/lib/api');
      const handleComplete = jest.fn();
      const syncResponse = {
        success: true,
        message: 'Synced successfully',
      };

      apiRequest.mockResolvedValueOnce(mockDiffResponse);
      apiRequest.mockResolvedValueOnce(syncResponse);

      render(
        <MergeWorkflow
          entityId="skill:test"
          projectPath="/test/project"
          direction="upstream"
          onComplete={handleComplete}
          onCancel={jest.fn()}
        />
      );

      // Navigate and apply
      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
      });

      await waitFor(() => {
        fireEvent.click(screen.getByRole('button', { name: /Apply Changes/ }));
      });

      // Wait for onComplete to be called (after 2s delay)
      await waitFor(
        () => {
          expect(handleComplete).toHaveBeenCalled();
        },
        { timeout: 3000 }
      );
    });
  });

  it('renders all progress steps during apply', async () => {
    const { apiRequest } = require('@/lib/api');
    apiRequest.mockResolvedValueOnce(mockDiffResponse);

    render(
      <MergeWorkflow
        entityId="skill:test"
        projectPath="/test/project"
        direction="upstream"
        onComplete={jest.fn()}
        onCancel={jest.fn()}
      />
    );

    // Navigate to Apply step
    await waitFor(() => {
      fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    });

    await waitFor(() => {
      fireEvent.click(screen.getByRole('button', { name: /Continue/ }));
    });

    await waitFor(() => {
      expect(screen.getByText('Apply Changes')).toBeInTheDocument();
    });
  });
});
