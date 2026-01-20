/**
 * Accessibility Tests for BulkImportModal
 *
 * Tests for DIS-5.7: Skip Checkbox Accessibility Audit
 * Verifies:
 * - Label associations
 * - Keyboard navigation
 * - Screen reader support
 * - Focus management
 * - Disabled state handling
 */

import { render, screen, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { BulkImportModal } from '@/components/discovery/BulkImportModal';
import { NotificationProvider } from '@/lib/notification-store';
import type { DiscoveredArtifact } from '@/components/discovery/BulkImportModal';

expect.extend(toHaveNoViolations);

/**
 * Test wrapper with NotificationProvider
 */
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <NotificationProvider>{children}</NotificationProvider>;
}

describe('BulkImportModal - Accessibility (DIS-5.7)', () => {
  const mockArtifacts: DiscoveredArtifact[] = [
    {
      type: 'skill',
      name: 'canvas-design',
      source: 'anthropics/skills/canvas-design',
      version: '1.0.0',
      path: '/path/to/skill',
      discovered_at: '2024-12-01T10:00:00Z',
      status: 'success',
    },
    {
      type: 'command',
      name: 'docker-compose',
      source: 'user/repo/commands/docker',
      version: '2.0.0',
      path: '/path/to/command',
      discovered_at: '2024-12-01T11:00:00Z',
      status: 'skipped',
    },
    {
      type: 'agent',
      name: 'code-reviewer',
      source: 'team/agents/reviewer',
      version: '1.5.0',
      path: '/path/to/agent',
      discovered_at: '2024-12-01T12:00:00Z',
    },
  ];

  const mockOnImport = jest.fn().mockResolvedValue({
    total_requested: 2,
    total_imported: 2,
    total_failed: 0,
    results: [],
  });

  const defaultProps = {
    artifacts: mockArtifacts,
    open: true,
    onClose: jest.fn(),
    onImport: mockOnImport,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('1. Label Association', () => {
    it('has proper id/htmlFor association for skip checkboxes', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      mockArtifacts.forEach((artifact) => {
        const checkboxId = `skip-${artifact.path}`;
        const checkbox = document.getElementById(checkboxId);

        // Verify checkbox exists with correct id
        expect(checkbox).toBeInTheDocument();

        // Find the label associated with this specific checkbox
        const label = document.querySelector(`label[for="${checkboxId}"]`);
        expect(label).toBeInTheDocument();
        expect(label).toHaveTextContent('Skip');
      });
    });

    it('has descriptive aria-label on skip checkboxes', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const canvasSkipCheckbox = document.getElementById('skip-/path/to/skill');
      expect(canvasSkipCheckbox).toHaveAttribute(
        'aria-label',
        "Don't show canvas-design in future discoveries"
      );

      const dockerSkipCheckbox = document.getElementById('skip-/path/to/command');
      expect(dockerSkipCheckbox).toHaveAttribute(
        'aria-label',
        "Don't show docker-compose in future discoveries"
      );
    });

    it('has aria-label on artifact selection checkboxes', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const selectAllCheckbox = screen.getByLabelText('Select all artifacts');
      expect(selectAllCheckbox).toBeInTheDocument();

      mockArtifacts.forEach((artifact) => {
        const selectCheckbox = screen.getByLabelText(`Select ${artifact.name}`);
        expect(selectCheckbox).toBeInTheDocument();
      });
    });

    it('clicking label toggles skip checkbox', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const label = screen.getAllByText('Skip')[0].closest('label') as HTMLLabelElement;
      const checkboxId = label.getAttribute('for');
      const checkbox = document.getElementById(checkboxId!) as HTMLInputElement;

      // Initial state
      expect(checkbox).not.toBeChecked();

      // Click label
      fireEvent.click(label);

      // Checkbox should be checked
      expect(checkbox).toBeChecked();
    });
  });

  describe('2. Keyboard Accessibility', () => {
    it('skip checkboxes are focusable via Tab key', async () => {
      const user = userEvent.setup();
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Tab to first interactive element (likely close button or select all)
      await user.tab();

      // Continue tabbing to find skip checkboxes
      // Note: exact tab order depends on DOM order
      let skipCheckboxFound = false;
      for (let i = 0; i < 20 && !skipCheckboxFound; i++) {
        await user.tab();
        const focused = document.activeElement;
        if (focused?.id.startsWith('skip-')) {
          skipCheckboxFound = true;
          expect(focused).toHaveAttribute('role', 'checkbox');
        }
      }

      expect(skipCheckboxFound).toBe(true);
    });

    it('Space key toggles skip checkbox state', async () => {
      const user = userEvent.setup();
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const skipCheckbox = document.getElementById('skip-/path/to/skill') as HTMLElement;

      // Focus the checkbox
      skipCheckbox.focus();
      expect(document.activeElement).toBe(skipCheckbox);

      // Initial unchecked state
      expect(skipCheckbox).toHaveAttribute('data-state', 'unchecked');

      // Press Space to toggle
      await user.keyboard(' ');

      // Should now be checked
      expect(skipCheckbox).toHaveAttribute('data-state', 'checked');

      // Press Space again to toggle back
      await user.keyboard(' ');

      // Should be unchecked again
      expect(skipCheckbox).toHaveAttribute('data-state', 'unchecked');
    });

    it('focus indicator is visible on skip checkboxes', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const skipCheckbox = document.getElementById('skip-/path/to/skill') as HTMLElement;

      // Focus the checkbox
      skipCheckbox.focus();

      // Check for focus-visible styles (from checkbox.tsx)
      // Radix adds focus-visible ring, verify it's applied
      const styles = window.getComputedStyle(skipCheckbox);

      // The checkbox should have the focus-visible class from Radix
      expect(skipCheckbox.className).toContain('focus-visible:ring');
    });

    it('disabled skip checkboxes are not focusable', async () => {
      const user = userEvent.setup();
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // The second artifact (docker-compose) has status 'skipped', so should be disabled
      const disabledSkipCheckbox = document.getElementById('skip-/path/to/command') as HTMLElement;

      expect(disabledSkipCheckbox).toBeDisabled();

      // Try to focus it
      disabledSkipCheckbox.focus();

      // Should not be focused due to disabled state
      expect(document.activeElement).not.toBe(disabledSkipCheckbox);
    });
  });

  describe('3. Screen Reader Support', () => {
    it('announces checkbox state (checked/unchecked)', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const skipCheckbox = document.getElementById('skip-/path/to/skill') as HTMLElement;

      // Unchecked state
      expect(skipCheckbox).toHaveAttribute('role', 'checkbox');
      expect(skipCheckbox).toHaveAttribute('aria-checked', 'false');
      expect(skipCheckbox).toHaveAttribute('data-state', 'unchecked');

      // Click to check
      fireEvent.click(skipCheckbox);

      // Checked state
      expect(skipCheckbox).toHaveAttribute('aria-checked', 'true');
      expect(skipCheckbox).toHaveAttribute('data-state', 'checked');
    });

    it('announces associated artifact name via aria-label', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      mockArtifacts.forEach((artifact) => {
        const skipCheckbox = document.getElementById(`skip-${artifact.path}`) as HTMLElement;

        // aria-label should mention the artifact name
        const ariaLabel = skipCheckbox.getAttribute('aria-label');
        expect(ariaLabel).toContain(artifact.name);
        expect(ariaLabel).toContain("Don't show");
        expect(ariaLabel).toContain('future discoveries');
      });
    });

    it('announces disabled state for already-skipped artifacts', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // docker-compose is already skipped (status: 'skipped')
      const disabledSkipCheckbox = document.getElementById('skip-/path/to/command') as HTMLElement;

      // Radix UI uses data-disabled attribute
      expect(disabledSkipCheckbox).toHaveAttribute('data-disabled');
      expect(disabledSkipCheckbox).toBeDisabled();
    });

    it('provides loading state announcement', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Check for sr-only loading announcement
      const loadingAnnouncement = screen.queryByRole('status');

      // Should not be present initially
      expect(loadingAnnouncement).not.toBeInTheDocument();

      // TODO: Test during import - would need to trigger import and check
      // This would require mocking the import to be in-progress
    });

    it('table has proper semantic structure for screen readers', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Verify table structure
      const table = screen.getByRole('table');
      expect(table).toBeInTheDocument();

      // Verify column headers
      expect(screen.getByRole('columnheader', { name: /type/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /name/i })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: /skip future/i })).toBeInTheDocument();

      // Verify rows
      const rows = screen.getAllByRole('row');
      expect(rows.length).toBeGreaterThan(1); // Header + data rows
    });
  });

  describe('4. Disabled State Handling', () => {
    it('visually distinguishes disabled skip checkboxes', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const disabledSkipCheckbox = document.getElementById('skip-/path/to/command') as HTMLElement;

      expect(disabledSkipCheckbox).toBeDisabled();

      // Check for disabled styling (from checkbox.tsx: disabled:opacity-50)
      const styles = window.getComputedStyle(disabledSkipCheckbox);
      expect(disabledSkipCheckbox.className).toContain('disabled:opacity-50');
    });

    it('skip checkbox disabled when artifact already skipped', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // docker-compose has status 'skipped'
      const skipCheckbox = document.getElementById('skip-/path/to/command') as HTMLElement;

      expect(skipCheckbox).toBeDisabled();
      // Radix UI uses data-disabled attribute
      expect(skipCheckbox).toHaveAttribute('data-disabled');
    });

    it('skip checkbox disabled during import operation', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Initially enabled
      const skipCheckbox = document.getElementById('skip-/path/to/skill') as HTMLElement;
      expect(skipCheckbox).not.toBeDisabled();

      // TODO: Test during import - would need to trigger import and verify
      // This would require component state manipulation or async test
    });

    it('disabled checkbox cannot be toggled via keyboard', async () => {
      const user = userEvent.setup();
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const disabledSkipCheckbox = document.getElementById('skip-/path/to/command') as HTMLElement;

      // Try to focus and toggle
      disabledSkipCheckbox.focus();
      const initialState = disabledSkipCheckbox.getAttribute('data-state');

      await user.keyboard(' ');

      // State should not change
      expect(disabledSkipCheckbox.getAttribute('data-state')).toBe(initialState);
    });

    it('provides accessible reason for disabled state in UI', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Find the row for docker-compose (skipped artifact)
      const dockerRow = screen.getByText('docker-compose').closest('tr');
      expect(dockerRow).toBeInTheDocument();

      // Verify status badge indicates it's skipped
      const statusBadge = within(dockerRow!).getByText(/skipped/i);
      expect(statusBadge).toBeInTheDocument();

      // The badge provides visual context for why checkbox is disabled
    });
  });

  describe('5. Focus Management', () => {
    it('focuses first focusable element when modal opens', () => {
      const { rerender } = render(<BulkImportModal {...defaultProps} open={false} />, {
        wrapper: TestWrapper,
      });

      // Modal closed, nothing focused
      expect(document.activeElement).toBe(document.body);

      // Open modal
      rerender(<BulkImportModal {...defaultProps} open={true} />, { wrapper: TestWrapper } as any);

      // First focusable element should receive focus
      // Radix Dialog handles this automatically
      const activeElement = document.activeElement;
      expect(activeElement).not.toBe(document.body);
    });

    it('traps focus within modal', async () => {
      const user = userEvent.setup();
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Tab through all elements
      // Focus should stay within modal (Radix Dialog feature)
      const initialFocus = document.activeElement;

      // Tab many times
      for (let i = 0; i < 30; i++) {
        await user.tab();
      }

      // Focus should still be within the dialog
      const dialog = screen.getByRole('dialog');
      expect(dialog).toContainElement(document.activeElement);
    });

    it('restores focus when modal closes', () => {
      const { rerender } = render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Close modal
      rerender(<BulkImportModal {...defaultProps} open={false} />, { wrapper: TestWrapper } as any);

      // Focus should be restored to body (or trigger element if available)
      // Radix Dialog handles this
      expect(document.activeElement?.tagName).toBe('BODY');
    });
  });

  describe('6. ARIA Attributes and Roles', () => {
    it('dialog has proper ARIA role and labeling', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const dialog = screen.getByRole('dialog');
      expect(dialog).toBeInTheDocument();

      // Verify dialog title
      expect(screen.getByText('Review Discovered Artifacts')).toBeInTheDocument();

      // Verify dialog description
      expect(
        screen.getByText(/Select artifacts to import into your collection/)
      ).toBeInTheDocument();
    });

    it('uses aria-busy during import operation', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const tableContainer = screen.getByRole('table').closest('div[aria-busy]');

      // Initially not busy
      expect(tableContainer).toHaveAttribute('aria-busy', 'false');

      // TODO: Test during import - would show aria-busy="true"
    });

    it('edit buttons have descriptive aria-labels', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      mockArtifacts.forEach((artifact) => {
        const editButton = screen.getByLabelText(`Edit ${artifact.name}`);
        expect(editButton).toBeInTheDocument();
      });
    });

    it('select all checkbox has indeterminate state', () => {
      render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const selectAllCheckbox = screen.getByLabelText('Select all artifacts') as HTMLElement;

      // Initially unchecked, not indeterminate
      expect(selectAllCheckbox).toHaveAttribute('data-indeterminate', 'false');

      // Select one artifact (partial selection)
      const firstArtifactCheckbox = screen.getByLabelText(`Select ${mockArtifacts[0].name}`);
      fireEvent.click(firstArtifactCheckbox);

      // Should now show indeterminate
      expect(selectAllCheckbox).toHaveAttribute('data-indeterminate', 'true');
    });
  });

  describe('7. Automated Accessibility Testing (jest-axe)', () => {
    it('has no accessibility violations in default state', async () => {
      const { container } = render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no accessibility violations with mixed artifact states', async () => {
      const { container } = render(<BulkImportModal {...defaultProps} />, { wrapper: TestWrapper });

      // Select some artifacts
      const firstCheckbox = screen.getByLabelText(`Select ${mockArtifacts[0].name}`);
      fireEvent.click(firstCheckbox);

      // Toggle skip on one
      const skipCheckbox = document.getElementById('skip-/path/to/skill') as HTMLElement;
      fireEvent.click(skipCheckbox);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no accessibility violations with empty state', async () => {
      const { container } = render(<BulkImportModal {...defaultProps} artifacts={[]} />, {
        wrapper: TestWrapper,
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('8. Edge Cases and Error States', () => {
    it('handles missing artifact name gracefully', () => {
      const artifactsWithMissingName: DiscoveredArtifact[] = [
        {
          type: 'skill',
          name: '',
          path: '/path/to/unnamed',
          discovered_at: '2024-12-01T10:00:00Z',
        },
      ];

      render(<BulkImportModal {...defaultProps} artifacts={artifactsWithMissingName} />, {
        wrapper: TestWrapper,
      });

      // Should still render - checkbox exists even with empty name
      const checkbox = document.querySelector('[aria-label^="Select"]');
      expect(checkbox).toBeInTheDocument();
    });

    it('maintains accessibility with very long artifact names', () => {
      const longNameArtifact: DiscoveredArtifact[] = [
        {
          type: 'skill',
          name: 'very-long-artifact-name-that-exceeds-normal-length-limits-for-testing-purposes',
          path: '/path/to/long',
          discovered_at: '2024-12-01T10:00:00Z',
        },
      ];

      render(<BulkImportModal {...defaultProps} artifacts={longNameArtifact} />, {
        wrapper: TestWrapper,
      });

      const skipCheckbox = document.getElementById('skip-/path/to/long') as HTMLElement;
      const ariaLabel = skipCheckbox.getAttribute('aria-label');

      // aria-label should contain full name
      expect(ariaLabel).toContain(
        'very-long-artifact-name-that-exceeds-normal-length-limits-for-testing-purposes'
      );
    });
  });
});
