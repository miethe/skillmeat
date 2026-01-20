/**
 * Tests for GroupBadgeRow component
 *
 * Tests group membership badge display with overflow handling,
 * tooltip interactions, and accessibility features.
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  GroupBadgeRow,
  type GroupInfo,
} from '@/components/shared/group-badge-row';

// ============================================================================
// Test Data
// ============================================================================

const mockGroups: GroupInfo[] = [
  { id: '1', name: 'Priority Tasks' },
  { id: '2', name: 'Review Queue' },
  { id: '3', name: 'Archive' },
  { id: '4', name: 'Favorites' },
];

const singleGroup: GroupInfo[] = [{ id: '1', name: 'Priority Tasks' }];

const twoGroups: GroupInfo[] = [
  { id: '1', name: 'Priority Tasks' },
  { id: '2', name: 'Review Queue' },
];

const threeGroups: GroupInfo[] = [
  { id: '1', name: 'Priority Tasks' },
  { id: '2', name: 'Review Queue' },
  { id: '3', name: 'Archive' },
];

// ============================================================================
// Basic Rendering Tests
// ============================================================================

describe('GroupBadgeRow', () => {
  describe('Basic Rendering', () => {
    it('renders nothing when groups is empty array', () => {
      const { container } = render(<GroupBadgeRow groups={[]} />);
      expect(container.firstChild).toBeNull();
    });

    it('renders single badge when one group', () => {
      render(<GroupBadgeRow groups={singleGroup} />);

      const badge = screen.getByText('Priority Tasks');
      expect(badge).toBeInTheDocument();

      // Should not show overflow
      expect(screen.queryByText(/more\.\.\./)).not.toBeInTheDocument();
    });

    it('renders two badges when two groups', () => {
      render(<GroupBadgeRow groups={twoGroups} />);

      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
      expect(screen.getByText('Review Queue')).toBeInTheDocument();

      // Should not show overflow
      expect(screen.queryByText(/more\.\.\./)).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // Overflow Handling Tests
  // ============================================================================

  describe('Overflow Handling', () => {
    it('renders "+N more..." badge when >2 groups (default maxBadges)', () => {
      render(<GroupBadgeRow groups={threeGroups} />);

      // First two visible
      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
      expect(screen.getByText('Review Queue')).toBeInTheDocument();

      // Overflow badge showing remaining count
      expect(screen.getByText('+1 more...')).toBeInTheDocument();
    });

    it('shows correct count in overflow badge', () => {
      const manyGroups: GroupInfo[] = [
        { id: '1', name: 'One' },
        { id: '2', name: 'Two' },
        { id: '3', name: 'Three' },
        { id: '4', name: 'Four' },
        { id: '5', name: 'Five' },
      ];

      render(<GroupBadgeRow groups={manyGroups} />);

      // 5 total - 2 visible = 3 hidden
      expect(screen.getByText('+3 more...')).toBeInTheDocument();
    });

    it('respects custom maxBadges prop', () => {
      const groups: GroupInfo[] = [
        { id: '1', name: 'One' },
        { id: '2', name: 'Two' },
        { id: '3', name: 'Three' },
        { id: '4', name: 'Four' },
      ];

      render(<GroupBadgeRow groups={groups} maxBadges={3} />);

      // Should show 3 badges
      expect(screen.getByText('One')).toBeInTheDocument();
      expect(screen.getByText('Two')).toBeInTheDocument();
      expect(screen.getByText('Three')).toBeInTheDocument();

      // Only 1 hidden
      expect(screen.getByText('+1 more...')).toBeInTheDocument();
    });

    it('does not show overflow badge when groups equal maxBadges', () => {
      render(<GroupBadgeRow groups={twoGroups} maxBadges={2} />);

      expect(screen.queryByText(/more\.\.\./)).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // Tooltip Tests
  // ============================================================================

  describe('Tooltip', () => {
    it('tooltip shows remaining group names on hover', async () => {
      const user = userEvent.setup();
      render(<GroupBadgeRow groups={mockGroups} />);

      const overflowBadge = screen.getByText('+2 more...');
      await user.hover(overflowBadge);

      // Hidden groups should appear in tooltip (Radix renders duplicates for a11y)
      const archiveElements = await screen.findAllByText('Archive');
      expect(archiveElements.length).toBeGreaterThan(0);

      const favoritesElements = screen.getAllByText('Favorites');
      expect(favoritesElements.length).toBeGreaterThan(0);
    });

    it('tooltip is accessible via keyboard (tab focus)', async () => {
      const user = userEvent.setup();
      render(<GroupBadgeRow groups={mockGroups} />);

      // The overflow badge should be focusable (tabIndex={0})
      const overflowBadge = screen.getByText('+2 more...');
      expect(overflowBadge).toHaveAttribute('tabIndex', '0');

      // Tab to focus on badges
      await user.tab(); // First badge
      await user.tab(); // Second badge
      await user.tab(); // Overflow badge

      expect(overflowBadge).toHaveFocus();
    });
  });

  // ============================================================================
  // Accessibility Tests
  // ============================================================================

  describe('Accessibility', () => {
    it('each badge has correct aria-label', () => {
      render(<GroupBadgeRow groups={twoGroups} />);

      const priorityBadge = screen.getByLabelText('In group: Priority Tasks');
      const reviewBadge = screen.getByLabelText('In group: Review Queue');

      expect(priorityBadge).toBeInTheDocument();
      expect(reviewBadge).toBeInTheDocument();
    });

    it('overflow badge has aria-label listing hidden groups', () => {
      render(<GroupBadgeRow groups={mockGroups} />);

      const overflowBadge = screen.getByLabelText(
        '2 more groups: Archive, Favorites'
      );
      expect(overflowBadge).toBeInTheDocument();
    });

    it('container has role="list" attribute', () => {
      render(<GroupBadgeRow groups={singleGroup} />);

      const container = screen.getByRole('list');
      expect(container).toBeInTheDocument();
      expect(container).toHaveAttribute('aria-label', 'Group memberships');
    });

    it('individual badges are wrapped in role="listitem"', () => {
      render(<GroupBadgeRow groups={twoGroups} />);

      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(2);

      // Verify badges are within listitems
      expect(within(listItems[0]).getByText('Priority Tasks')).toBeInTheDocument();
      expect(within(listItems[1]).getByText('Review Queue')).toBeInTheDocument();
    });

    it('overflow badge is also wrapped in role="listitem"', () => {
      render(<GroupBadgeRow groups={threeGroups} />);

      const listItems = screen.getAllByRole('listitem');
      // 2 visible + 1 overflow
      expect(listItems).toHaveLength(3);

      // Last listitem should contain overflow badge
      expect(within(listItems[2]).getByText('+1 more...')).toBeInTheDocument();
    });

    it('badges are keyboard focusable', () => {
      render(<GroupBadgeRow groups={singleGroup} />);

      const badge = screen.getByText('Priority Tasks');
      expect(badge).toHaveAttribute('tabIndex', '0');
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles null groups gracefully', () => {
      // @ts-expect-error - Testing runtime behavior with invalid input
      const { container } = render(<GroupBadgeRow groups={null} />);
      expect(container.firstChild).toBeNull();
    });

    it('handles undefined groups gracefully', () => {
      // @ts-expect-error - Testing runtime behavior with invalid input
      const { container } = render(<GroupBadgeRow groups={undefined} />);
      expect(container.firstChild).toBeNull();
    });

    it('handles groups with null items gracefully', () => {
      const groupsWithNull = [
        { id: '1', name: 'Priority Tasks' },
        null,
        { id: '2', name: 'Review Queue' },
      ] as GroupInfo[];

      render(<GroupBadgeRow groups={groupsWithNull} />);

      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
      expect(screen.getByText('Review Queue')).toBeInTheDocument();
    });

    it('handles empty group names gracefully', () => {
      const groupsWithEmpty: GroupInfo[] = [
        { id: '1', name: '' },
        { id: '2', name: 'Valid' },
      ];

      render(<GroupBadgeRow groups={groupsWithEmpty} />);

      // Empty name groups should be filtered out by the component
      // Only Valid should be rendered
      expect(screen.getByText('Valid')).toBeInTheDocument();
    });

    it('handles groups with missing id gracefully', () => {
      const groupsWithMissingId = [
        { name: 'No ID' } as GroupInfo,
        { id: '2', name: 'Valid' },
      ];

      render(<GroupBadgeRow groups={groupsWithMissingId} />);

      // Missing id groups should be filtered out
      expect(screen.getByText('Valid')).toBeInTheDocument();
    });

    it('handles groups with missing name gracefully', () => {
      const groupsWithMissingName = [
        { id: '1' } as GroupInfo,
        { id: '2', name: 'Valid' },
      ];

      render(<GroupBadgeRow groups={groupsWithMissingName} />);

      // Missing name groups should be filtered out
      expect(screen.getByText('Valid')).toBeInTheDocument();
    });

    it('handles long group names with truncation', () => {
      const longNameGroup: GroupInfo[] = [
        {
          id: '1',
          name: 'This is a very long group name that should be truncated',
        },
      ];

      render(<GroupBadgeRow groups={longNameGroup} />);

      const badge = screen.getByText(
        'This is a very long group name that should be truncated'
      );
      expect(badge).toBeInTheDocument();
      // Badge should have truncate class for CSS truncation
      expect(badge).toHaveClass('truncate');
    });

    it('handles maxBadges of 0', () => {
      render(<GroupBadgeRow groups={twoGroups} maxBadges={0} />);

      // All should be in overflow
      expect(screen.queryByText('Priority Tasks')).not.toBeInTheDocument();
      expect(screen.queryByText('Review Queue')).not.toBeInTheDocument();
      expect(screen.getByText('+2 more...')).toBeInTheDocument();
    });

    it('handles maxBadges of 1', () => {
      render(<GroupBadgeRow groups={twoGroups} maxBadges={1} />);

      expect(screen.getByText('Priority Tasks')).toBeInTheDocument();
      expect(screen.queryByText('Review Queue')).not.toBeInTheDocument();
      expect(screen.getByText('+1 more...')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Custom Styling Tests
  // ============================================================================

  describe('Custom Styling', () => {
    it('applies custom className to container', () => {
      render(<GroupBadgeRow groups={singleGroup} className="custom-class" />);

      const container = screen.getByRole('list');
      expect(container).toHaveClass('custom-class');
    });

    it('preserves default classes when custom className is added', () => {
      render(<GroupBadgeRow groups={singleGroup} className="custom-class" />);

      const container = screen.getByRole('list');
      expect(container).toHaveClass('inline-flex');
      expect(container).toHaveClass('custom-class');
    });
  });
});
