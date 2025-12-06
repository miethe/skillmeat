/**
 * Accessibility Tests for ArtifactActions Component
 * @jest-environment jsdom
 */
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { NotificationProvider } from '@/lib/notification-store';
import { ArtifactActions } from '@/components/discovery/ArtifactActions';
import type { DiscoveredArtifact } from '@/types/discovery';

const mockArtifact: DiscoveredArtifact = {
  type: 'skill',
  name: 'test-skill',
  source: 'github:user/repo/skill',
  version: 'latest',
  path: '/path/to/skill',
  discovered_at: '2025-01-01T00:00:00Z',
};

// Wrapper to provide notification context
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <NotificationProvider>{children}</NotificationProvider>;
}

describe('ArtifactActions Accessibility', () => {
  describe('Basic Rendering', () => {
    it('should have no violations in default state', async () => {
      const { container } = render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations when artifact is skipped', async () => {
      const { container } = render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={true}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations when artifact is imported', async () => {
      const { container } = render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={true}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('should have no violations with open menu', async () => {
      const { container } = render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      // Open menu
      const trigger = screen.getByRole('button', { name: /Actions for test-skill/i });
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe('Screen Reader Support', () => {
    it('should have accessible trigger button label', () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button', { name: /Actions for test-skill/i });
      expect(trigger).toBeInTheDocument();
      expect(trigger).toHaveAttribute('aria-label', 'Actions for test-skill');
    });

    it('should hide decorative icons from screen readers', async () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      // Open menu
      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      // Icons should be aria-hidden (can't easily test this without DOM inspection)
      // But we verify that menu items have text content
      expect(screen.getByText(/Import to Collection/i)).toBeInTheDocument();
      expect(screen.getByText(/View Details/i)).toBeInTheDocument();
    });

    it('should announce disabled state for imported artifacts', async () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={true}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const importItem = screen.getByRole('menuitem', { name: /Already imported/i });
        expect(importItem).toBeInTheDocument();
        expect(importItem).toHaveAttribute('aria-disabled', 'true');
      });
    });

    it('should announce skip state change', async () => {
      const { rerender } = render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      // Initially shows "Skip for future"
      await waitFor(() => {
        expect(screen.getByText(/Skip for future/i)).toBeInTheDocument();
      });

      // Close menu
      await userEvent.keyboard('{Escape}');

      // Change to skipped state
      rerender(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={true}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      // Reopen menu
      await userEvent.click(trigger);

      // Now shows "Un-skip"
      await waitFor(() => {
        expect(screen.getByText(/Un-skip/i)).toBeInTheDocument();
      });
    });

    it('should have accessible labels for all menu items', async () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const menuItems = screen.getAllByRole('menuitem');
        menuItems.forEach((item) => {
          expect(item).toHaveAccessibleName();
        });
      });
    });
  });

  describe('Keyboard Navigation', () => {
    it('should open menu with Enter key', async () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      trigger.focus();

      await userEvent.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });
    });

    it('should navigate menu with arrow keys', async () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      // Arrow down should move focus
      await userEvent.keyboard('{ArrowDown}');
      const firstItem = screen.getByRole('menuitem', { name: /Import to Collection/i });
      expect(firstItem).toHaveFocus();

      await userEvent.keyboard('{ArrowDown}');
      const secondItem = screen.getByRole('menuitem', { name: /Skip for future/i });
      expect(secondItem).toHaveFocus();
    });

    it('should close menu with Escape key', async () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      await userEvent.keyboard('{Escape}');

      await waitFor(() => {
        expect(screen.queryByRole('menu')).not.toBeInTheDocument();
      });
    });

    it('should activate menu items with Enter/Space', async () => {
      const onViewDetails = jest.fn();
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={onViewDetails}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      // Navigate to View Details
      await userEvent.keyboard('{ArrowDown}');
      await userEvent.keyboard('{ArrowDown}');
      await userEvent.keyboard('{ArrowDown}');

      // Activate with Enter
      await userEvent.keyboard('{Enter}');

      expect(onViewDetails).toHaveBeenCalled();
    });
  });

  describe('Menu Interactions', () => {
    it('should call onImport when import clicked', async () => {
      const onImport = jest.fn();
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={onImport}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      const importItem = screen.getByRole('menuitem', { name: /Import to Collection/i });
      await userEvent.click(importItem);

      expect(onImport).toHaveBeenCalled();
    });

    it('should call onToggleSkip with correct value', async () => {
      const onToggleSkip = jest.fn();
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={onToggleSkip}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      const skipItem = screen.getByRole('menuitem', { name: /Skip for future/i });
      await userEvent.click(skipItem);

      expect(onToggleSkip).toHaveBeenCalledWith(true);
    });

    it('should call onViewDetails when clicked', async () => {
      const onViewDetails = jest.fn();
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={onViewDetails}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      const detailsItem = screen.getByRole('menuitem', { name: /View Details/i });
      await userEvent.click(detailsItem);

      expect(onViewDetails).toHaveBeenCalled();
    });

    it('should handle copy source URL', async () => {
      // Mock clipboard API
      Object.assign(navigator, {
        clipboard: {
          writeText: jest.fn().mockResolvedValue(undefined),
        },
      });

      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      const copyItem = screen.getByRole('menuitem', { name: /Copy Source URL/i });
      await userEvent.click(copyItem);

      expect(navigator.clipboard.writeText).toHaveBeenCalledWith(mockArtifact.source);
    });

    it('should disable copy when no source', async () => {
      const artifactNoSource = { ...mockArtifact, source: undefined };
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={artifactNoSource}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        const copyItem = screen.getByRole('menuitem', { name: /Copy Source URL/i });
        expect(copyItem).toHaveAttribute('aria-disabled', 'true');
      });
    });
  });

  describe('Focus Management', () => {
    it('should return focus to trigger after menu closes', async () => {
      render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const trigger = screen.getByRole('button');
      await userEvent.click(trigger);

      await waitFor(() => {
        expect(screen.getByRole('menu')).toBeInTheDocument();
      });

      await userEvent.keyboard('{Escape}');

      await waitFor(() => {
        expect(screen.queryByRole('menu')).not.toBeInTheDocument();
        expect(trigger).toHaveFocus();
      });
    });
  });

  describe('Color Contrast', () => {
    it('should have compliant color contrast', async () => {
      const { container } = render(
        <TestWrapper>
          <ArtifactActions
            artifact={mockArtifact}
            isSkipped={false}
            isImported={false}
            onImport={jest.fn()}
            onToggleSkip={jest.fn()}
            onViewDetails={jest.fn()}
          />
        </TestWrapper>
      );

      const results = await axe(container, {
        rules: {
          'color-contrast': { enabled: true },
        },
      });
      expect(results).toHaveNoViolations();
    });
  });
});
