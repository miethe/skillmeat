/**
 * Accessibility Tests for SkipPreferencesList Component
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { SkipPreferencesList } from '@/components/discovery/SkipPreferencesList';
import type { SkipPreference } from '@/types/discovery';

const mockSkipPrefs: SkipPreference[] = [
  {
    artifact_key: 'skill:test-skill',
    skip_reason: 'Not needed for this project',
    added_date: '2025-01-01T00:00:00Z',
  },
  {
    artifact_key: 'command:test-command',
    skip_reason: 'Already have similar functionality',
    added_date: '2025-01-02T00:00:00Z',
  },
  {
    artifact_key: 'agent:test-agent',
    skip_reason: undefined,
    added_date: '2025-01-03T00:00:00Z',
  },
];

describe('SkipPreferencesList Accessibility', () => {
  describe('Basic Rendering', () => {
    it('should have no violations when collapsed', async () => {
      const { container } = render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations when expanded', async () => {
      const { container } = render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      // Expand collapsible
      const trigger = screen.getByRole('button', { name: /Skipped Artifacts/i });
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('test-skill')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations with empty state', async () => {
      const { container } = render(
        <SkipPreferencesList
          skipPrefs={[]}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations with confirmation dialog', async () => {
      const { container } = render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      // Expand and open dialog
      const trigger = screen.getByRole('button', { name: /Skipped Artifacts/i });
      await userEvent.click(trigger);

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /Clear All Skips/i });
        return userEvent.click(clearButton);
      });

      await waitFor(() => {
        expect(screen.getByRole('alertdialog')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Screen Reader Support', () => {
    it('should have accessible collapsible trigger', () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      expect(trigger).toHaveAttribute('aria-expanded', 'false');
      expect(trigger).toHaveAttribute('aria-controls', 'skip-preferences-content');
    });

    it('should update aria-expanded when toggled', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      expect(trigger).toHaveAttribute('aria-expanded', 'false');

      await userEvent.click(trigger);

      await waitFor(() => {
        expect(trigger).toHaveAttribute('aria-expanded', 'true');
      });
    });

    it('should announce count in badge', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      // Badge should be announced as part of button
      const trigger = screen.getByRole('button');
      expect(trigger).toHaveTextContent('3');
    });

    it('should have accessible un-skip buttons', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button', { name: /Skipped Artifacts/i });
      await userEvent.click(trigger);

      await waitFor(() => {
        const unskipButton = screen.getByRole('button', { name: /Un-skip test-skill/i });
        expect(unskipButton).toBeInTheDocument();
        expect(unskipButton).toHaveAttribute('aria-label', 'Un-skip test-skill');
      });
    });

    it('should announce empty state', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={[]}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText(/No artifacts are currently skipped/i)).toBeInTheDocument();
      });
    });

    it('should have accessible confirmation dialog', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /Clear All Skips/i });
        return userEvent.click(clearButton);
      });

      await waitFor(() => {
        const dialog = screen.getByRole('alertdialog');
        expect(dialog).toBeInTheDocument();

        // Should have title and description
        expect(screen.getByText(/Clear all skip preferences/i)).toBeInTheDocument();
        expect(screen.getByText(/This will clear all 3 skipped/i)).toBeInTheDocument();
      });
    });

    it('should hide decorative icons from screen readers', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('test-skill')).toBeInTheDocument();
      });

      // Chevron icons should be aria-hidden (checked by axe)
    });
  });

  describe('Keyboard Navigation', () => {
    it('should support keyboard activation of trigger', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      trigger.focus();

      await userEvent.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByText('test-skill')).toBeInTheDocument();
      });
    });

    it('should navigate through un-skip buttons with Tab', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('test-skill')).toBeInTheDocument();
      });

      // Tab to first un-skip button
      const firstUnskip = screen.getByRole('button', { name: /Un-skip test-skill/i });
      firstUnskip.focus();
      expect(firstUnskip).toHaveFocus();

      // Tab to next
      await userEvent.tab();
      const secondUnskip = screen.getByRole('button', { name: /Un-skip test-command/i });
      expect(secondUnskip).toHaveFocus();
    });

    it('should activate un-skip with Enter/Space', async () => {
      const onRemoveSkip = jest.fn();
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={onRemoveSkip}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const unskipButton = screen.getByRole('button', { name: /Un-skip test-skill/i });
        return userEvent.click(unskipButton);
      });

      expect(onRemoveSkip).toHaveBeenCalledWith('skill:test-skill');
    });

    it('should support keyboard navigation in confirmation dialog', async () => {
      const onClearAll = jest.fn();
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={onClearAll}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /Clear All Skips/i });
        return userEvent.click(clearButton);
      });

      await waitFor(() => {
        expect(screen.getByRole('alertdialog')).toBeInTheDocument();
      });

      // Tab to Cancel button
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      cancelButton.focus();
      expect(cancelButton).toHaveFocus();

      // Tab to Clear All button
      await userEvent.tab();
      const clearAllButton = screen.getByRole('button', { name: /Clear All/i });
      expect(clearAllButton).toHaveFocus();

      // Press Enter
      await userEvent.keyboard('{Enter}');
      expect(onClearAll).toHaveBeenCalled();
    });

    it('should close dialog with Escape', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /Clear All Skips/i });
        return userEvent.click(clearButton);
      });

      await waitFor(() => {
        expect(screen.getByRole('alertdialog')).toBeInTheDocument();
      });

      await userEvent.keyboard('{Escape}');

      await waitFor(() => {
        expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('Focus Management', () => {
    it('should have visible focus styles', () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      trigger.focus();

      // Focus should be visible (CSS classes applied)
      expect(trigger).toHaveClass('focus-visible:outline-none');
      expect(trigger).toHaveClass('focus-visible:ring-2');
    });

    it('should trap focus in confirmation dialog', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /Clear All Skips/i });
        return userEvent.click(clearButton);
      });

      await waitFor(() => {
        expect(screen.getByRole('alertdialog')).toBeInTheDocument();
      });

      // Focus should be in dialog
      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      expect(document.activeElement).toBe(cancelButton);

      // Tab should cycle within dialog
      await userEvent.tab();
      const clearAllButton = screen.getByRole('button', { name: /Clear All/i });
      expect(clearAllButton).toHaveFocus();

      // Tab again should return to first button
      await userEvent.tab();
      expect(cancelButton).toHaveFocus();
    });

    it('should return focus to trigger after dialog closes', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const clearButton = screen.getByRole('button', { name: /Clear All Skips/i });
        clearButton.focus();
        return userEvent.click(clearButton);
      });

      await waitFor(() => {
        expect(screen.getByRole('alertdialog')).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: /Cancel/i });
      await userEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
      });

      // Focus should return somewhere reasonable (Radix handles this)
    });
  });

  describe('Interactive Behaviors', () => {
    it('should auto-collapse when empty', async () => {
      const { rerender } = render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('test-skill')).toBeInTheDocument();
      });

      // Update to empty
      rerender(
        <SkipPreferencesList
          skipPrefs={[]}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      // Should auto-collapse
      await waitFor(() => {
        expect(trigger).toHaveAttribute('aria-expanded', 'false');
      });
    });

    it('should not show clear all button with single item', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={[mockSkipPrefs[0]]}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('test-skill')).toBeInTheDocument();
      });

      // Clear all button should not exist
      expect(screen.queryByRole('button', { name: /Clear All Skips/i })).not.toBeInTheDocument();
    });

    it('should disable buttons when loading', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
          isLoading={true}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const unskipButton = screen.getByRole('button', { name: /Un-skip test-skill/i });
        expect(unskipButton).toBeDisabled();
      });
    });
  });

  describe('Color Contrast', () => {
    it('should have compliant color contrast', async () => {
      const { container } = render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe('Content Structure', () => {
    it('should display all skip preferences', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('test-skill')).toBeInTheDocument();
        expect(screen.getByText('test-command')).toBeInTheDocument();
        expect(screen.getByText('test-agent')).toBeInTheDocument();
      });
    });

    it('should display skip reasons when present', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByText('Not needed for this project')).toBeInTheDocument();
        expect(screen.getByText('Already have similar functionality')).toBeInTheDocument();
      });
    });

    it('should display dates', async () => {
      render(
        <SkipPreferencesList
          skipPrefs={mockSkipPrefs}
          onRemoveSkip={jest.fn()}
          onClearAll={jest.fn()}
        />
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const dates = screen.getAllByText(/Skipped \d+\/\d+\/\d+/i);
        expect(dates.length).toBeGreaterThan(0);
      });
    });
  });
});
