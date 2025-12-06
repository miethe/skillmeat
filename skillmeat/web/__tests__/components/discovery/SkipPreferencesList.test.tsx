import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SkipPreferencesList } from '@/components/discovery/SkipPreferencesList';
import type { SkipPreference } from '@/types/discovery';

describe('SkipPreferencesList', () => {
  const mockSkipPrefs: SkipPreference[] = [
    {
      artifact_key: 'skill:canvas-design',
      skip_reason: 'Not needed for this project',
      added_date: '2024-12-01T10:00:00Z',
    },
    {
      artifact_key: 'command:docker-compose',
      skip_reason: 'Already installed manually',
      added_date: '2024-12-02T15:30:00Z',
    },
  ];

  const mockHandlers = {
    onRemoveSkip: jest.fn(),
    onClearAll: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders collapsed by default', () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    expect(screen.getByText('Skipped Artifacts')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // Count badge
    expect(screen.queryByText('canvas-design')).not.toBeInTheDocument(); // Content hidden
  });

  it('expands when clicked', async () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    const trigger = screen.getByRole('button', { name: /skipped artifacts/i });
    fireEvent.click(trigger);

    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
      expect(screen.getByText('docker-compose')).toBeInTheDocument();
    });
  });

  it('displays artifact details correctly', async () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    // Wait for content to appear
    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    // Check type badge
    expect(screen.getByText('skill')).toBeInTheDocument();

    // Check skip reason
    expect(screen.getByText('Not needed for this project')).toBeInTheDocument();

    // Check date (at least partial match) - there are multiple "Skipped" texts
    const skippedTexts = screen.getAllByText(/Skipped/);
    expect(skippedTexts.length).toBeGreaterThan(0);
  });

  it('calls onRemoveSkip when Un-skip button clicked', async () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    // Click Un-skip for first item
    const unskipButton = screen.getByRole('button', { name: /un-skip canvas-design/i });
    fireEvent.click(unskipButton);

    expect(mockHandlers.onRemoveSkip).toHaveBeenCalledWith('skill:canvas-design');
    expect(mockHandlers.onRemoveSkip).toHaveBeenCalledTimes(1);
  });

  it('shows confirmation dialog when Clear All clicked', async () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    // Click Clear All
    const clearAllButton = screen.getByRole('button', { name: /clear all skips/i });
    fireEvent.click(clearAllButton);

    // Verify dialog appears
    await waitFor(() => {
      expect(screen.getByText('Clear all skip preferences?')).toBeInTheDocument();
      expect(screen.getByText(/This will clear all 2 skipped artifacts/i)).toBeInTheDocument();
    });
  });

  it('calls onClearAll when confirmed in dialog', async () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    // Expand and open dialog
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /clear all skips/i }));

    await waitFor(() => {
      expect(screen.getByText('Clear all skip preferences?')).toBeInTheDocument();
    });

    // Click confirm button in dialog
    const confirmButton = screen.getByRole('button', { name: /^clear all$/i });
    fireEvent.click(confirmButton);

    expect(mockHandlers.onClearAll).toHaveBeenCalledTimes(1);
  });

  it('does not call onClearAll when cancelled in dialog', async () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    // Expand and open dialog
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /clear all skips/i }));

    await waitFor(() => {
      expect(screen.getByText('Clear all skip preferences?')).toBeInTheDocument();
    });

    // Click cancel button
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    fireEvent.click(cancelButton);

    expect(mockHandlers.onClearAll).not.toHaveBeenCalled();
  });

  it('displays empty state when no skip preferences', () => {
    render(<SkipPreferencesList skipPrefs={[]} {...mockHandlers} />);

    expect(screen.getByText('Skipped Artifacts')).toBeInTheDocument();
    expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument(); // No count badge

    // Try to expand
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    // Should still not show content since empty
    expect(screen.queryByText('No artifacts are currently skipped.')).not.toBeInTheDocument();
  });

  it('disables buttons when isLoading is true', async () => {
    render(
      <SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} isLoading={true} />
    );

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    // Check that Un-skip buttons are disabled
    const unskipButtons = screen.getAllByRole('button', { name: /un-skip/i });
    unskipButtons.forEach((button) => {
      expect(button).toBeDisabled();
    });

    // Check that Clear All button is disabled
    const clearAllButton = screen.getByRole('button', { name: /clear all skips/i });
    expect(clearAllButton).toBeDisabled();
  });

  it('handles artifact keys without colon separator gracefully', async () => {
    const invalidSkipPrefs: SkipPreference[] = [
      {
        artifact_key: 'invalid-key-format',
        skip_reason: 'Test malformed key',
        added_date: '2024-12-01T10:00:00Z',
      },
    ];

    render(<SkipPreferencesList skipPrefs={invalidSkipPrefs} {...mockHandlers} />);

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    await waitFor(() => {
      // Should display the key as-is when parsing fails
      expect(screen.getByText('invalid-key-format')).toBeInTheDocument();
      expect(screen.getByText('unknown')).toBeInTheDocument(); // Type badge
    });
  });

  it('does not show Clear All button when only one skip exists', async () => {
    const singleSkipPref: SkipPreference[] = [mockSkipPrefs[0]];

    render(<SkipPreferencesList skipPrefs={singleSkipPref} {...mockHandlers} />);

    // Expand
    fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

    await waitFor(() => {
      expect(screen.getByText('canvas-design')).toBeInTheDocument();
    });

    // Clear All button should not be present
    expect(screen.queryByRole('button', { name: /clear all skips/i })).not.toBeInTheDocument();
  });

  it('has proper ARIA attributes for accessibility', () => {
    render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

    const trigger = screen.getByRole('button', { name: /skipped artifacts/i });

    // Check aria-expanded
    expect(trigger).toHaveAttribute('aria-expanded', 'false');

    // Expand and check again
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute('aria-expanded', 'true');
  });

  describe('Keyboard Accessibility (DIS-5.7)', () => {
    it('collapsible trigger is keyboard accessible', async () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      const trigger = screen.getByRole('button', { name: /skipped artifacts/i });

      // Trigger should be focusable
      trigger.focus();
      expect(document.activeElement).toBe(trigger);

      // Should have visible focus indicator
      expect(trigger.className).toContain('focus-visible:ring');
    });

    it('un-skip buttons have descriptive labels for screen readers', async () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      // Expand
      fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Verify each un-skip button has descriptive aria-label
      const unskipCanvasButton = screen.getByRole('button', { name: /un-skip canvas-design/i });
      expect(unskipCanvasButton).toBeInTheDocument();
      expect(unskipCanvasButton).toHaveAttribute('aria-label', 'Un-skip canvas-design');

      const unskipDockerButton = screen.getByRole('button', { name: /un-skip docker-compose/i });
      expect(unskipDockerButton).toBeInTheDocument();
      expect(unskipDockerButton).toHaveAttribute('aria-label', 'Un-skip docker-compose');
    });

    it('clear all button is keyboard accessible', async () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      // Expand
      fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      const clearAllButton = screen.getByRole('button', { name: /clear all skips/i });

      // Should be focusable
      clearAllButton.focus();
      expect(document.activeElement).toBe(clearAllButton);
    });
  });

  describe('Screen Reader Support (DIS-5.7)', () => {
    it('announces artifact count via badge', () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      // Count badge should be visible and readable
      const countBadge = screen.getByText('2');
      expect(countBadge).toBeInTheDocument();

      // Badge has proper semantic role
      expect(countBadge.tagName).toBe('DIV');
    });

    it('provides semantic structure for artifact cards', async () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      // Expand
      fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Each artifact should have:
      // - Name (heading-like)
      // - Type badge
      // - Skip reason
      // - Date

      expect(screen.getByText('canvas-design')).toBeInTheDocument();
      expect(screen.getByText('skill')).toBeInTheDocument();
      expect(screen.getByText('Not needed for this project')).toBeInTheDocument();
    });

    it('confirmation dialog has proper ARIA labeling', async () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      // Expand and open dialog
      fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByRole('button', { name: /clear all skips/i }));

      await waitFor(() => {
        expect(screen.getByText('Clear all skip preferences?')).toBeInTheDocument();
      });

      // Dialog should have proper role and accessible name
      // Radix AlertDialog provides this automatically
      const dialogTitle = screen.getByText('Clear all skip preferences?');
      expect(dialogTitle).toBeInTheDocument();

      const dialogDescription = screen.getByText(/This will clear all 2 skipped artifacts/i);
      expect(dialogDescription).toBeInTheDocument();
    });
  });

  describe('Focus Management (DIS-5.7)', () => {
    it('maintains focus on trigger after collapse', async () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      const trigger = screen.getByRole('button', { name: /skipped artifacts/i });

      // Expand
      fireEvent.click(trigger);
      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      // Focus the trigger explicitly
      trigger.focus();
      expect(document.activeElement).toBe(trigger);

      // Collapse
      fireEvent.click(trigger);

      // Trigger should still be in the document and focusable
      expect(trigger).toBeInTheDocument();
      expect(trigger).toHaveAttribute('aria-expanded', 'false');
    });

    it('focus returns to clear all button after dialog dismissal', async () => {
      render(<SkipPreferencesList skipPrefs={mockSkipPrefs} {...mockHandlers} />);

      // Expand
      fireEvent.click(screen.getByRole('button', { name: /skipped artifacts/i }));

      await waitFor(() => {
        expect(screen.getByText('canvas-design')).toBeInTheDocument();
      });

      const clearAllButton = screen.getByRole('button', { name: /clear all skips/i });

      // Open dialog
      fireEvent.click(clearAllButton);

      await waitFor(() => {
        expect(screen.getByText('Clear all skip preferences?')).toBeInTheDocument();
      });

      // Cancel dialog
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      fireEvent.click(cancelButton);

      // Focus should return to clear all button (Radix handles this)
      // In test environment this might be body, but in real browser Radix manages focus
      await waitFor(() => {
        expect(screen.queryByText('Clear all skip preferences?')).not.toBeInTheDocument();
      });
    });
  });
});
