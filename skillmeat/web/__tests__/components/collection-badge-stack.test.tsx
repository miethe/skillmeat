/**
 * Tests for CollectionBadgeStack component
 *
 * Tests collection membership badge display with overflow handling,
 * tooltip interactions, and accessibility features.
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CollectionBadgeStack, CollectionInfo } from '@/components/shared/collection-badge-stack';

// ============================================================================
// Test Data
// ============================================================================

const mockCollections: CollectionInfo[] = [
  { id: '1', name: 'Work', is_default: false },
  { id: '2', name: 'Personal', is_default: false },
  { id: '3', name: 'Archive', is_default: false },
  { id: '4', name: 'Favorites', is_default: false },
  { id: 'default', name: 'Default', is_default: true },
];

const singleCollection: CollectionInfo[] = [{ id: '1', name: 'Work', is_default: false }];

const twoCollections: CollectionInfo[] = [
  { id: '1', name: 'Work', is_default: false },
  { id: '2', name: 'Personal', is_default: false },
];

const onlyDefaultCollection: CollectionInfo[] = [
  { id: 'default', name: 'Default', is_default: true },
];

const mixedCollections: CollectionInfo[] = [
  { id: 'default', name: 'Default', is_default: true },
  { id: '1', name: 'Work', is_default: false },
  { id: '2', name: 'Personal', is_default: false },
];

// ============================================================================
// Basic Rendering Tests
// ============================================================================

describe('CollectionBadgeStack', () => {
  describe('Basic Rendering', () => {
    it('renders nothing when collections is empty array', () => {
      const { container } = render(<CollectionBadgeStack collections={[]} />);
      expect(container.firstChild).toBeNull();
    });

    it('renders nothing when all collections are default', () => {
      const { container } = render(<CollectionBadgeStack collections={onlyDefaultCollection} />);
      expect(container.firstChild).toBeNull();
    });

    it('renders single badge when one non-default collection', () => {
      render(<CollectionBadgeStack collections={singleCollection} />);

      const badge = screen.getByText('Work');
      expect(badge).toBeInTheDocument();

      // Should not show overflow
      expect(screen.queryByText(/more\.\.\./)).not.toBeInTheDocument();
    });

    it('renders two badges when two non-default collections', () => {
      render(<CollectionBadgeStack collections={twoCollections} />);

      expect(screen.getByText('Work')).toBeInTheDocument();
      expect(screen.getByText('Personal')).toBeInTheDocument();

      // Should not show overflow
      expect(screen.queryByText(/more\.\.\./)).not.toBeInTheDocument();
    });

    it('filters out default collections and renders remaining', () => {
      render(<CollectionBadgeStack collections={mixedCollections} />);

      // Default collection should not be rendered
      expect(screen.queryByText('Default')).not.toBeInTheDocument();

      // Non-default collections should be rendered
      expect(screen.getByText('Work')).toBeInTheDocument();
      expect(screen.getByText('Personal')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Overflow Handling Tests
  // ============================================================================

  describe('Overflow Handling', () => {
    it('renders "+N more..." badge when >2 collections (default maxBadges)', () => {
      render(<CollectionBadgeStack collections={mockCollections} />);

      // First two visible
      expect(screen.getByText('Work')).toBeInTheDocument();
      expect(screen.getByText('Personal')).toBeInTheDocument();

      // Overflow badge showing remaining count (4 non-default - 2 visible = 2 hidden)
      expect(screen.getByText('+2 more...')).toBeInTheDocument();
    });

    it('shows correct count in overflow badge', () => {
      const manyCollections: CollectionInfo[] = [
        { id: '1', name: 'One', is_default: false },
        { id: '2', name: 'Two', is_default: false },
        { id: '3', name: 'Three', is_default: false },
        { id: '4', name: 'Four', is_default: false },
        { id: '5', name: 'Five', is_default: false },
      ];

      render(<CollectionBadgeStack collections={manyCollections} />);

      // 5 total - 2 visible = 3 hidden
      expect(screen.getByText('+3 more...')).toBeInTheDocument();
    });

    it('filters out default collections before counting overflow', () => {
      const collectionsWithDefault: CollectionInfo[] = [
        { id: '1', name: 'One', is_default: false },
        { id: '2', name: 'Two', is_default: false },
        { id: '3', name: 'Three', is_default: false },
        { id: 'default', name: 'Default Collection', is_default: true },
      ];

      render(<CollectionBadgeStack collections={collectionsWithDefault} />);

      // Only 3 non-default, so 1 hidden
      expect(screen.getByText('+1 more...')).toBeInTheDocument();

      // Default should not appear anywhere
      expect(screen.queryByText('Default Collection')).not.toBeInTheDocument();
    });

    it('respects custom maxBadges prop', () => {
      const collections: CollectionInfo[] = [
        { id: '1', name: 'One', is_default: false },
        { id: '2', name: 'Two', is_default: false },
        { id: '3', name: 'Three', is_default: false },
        { id: '4', name: 'Four', is_default: false },
      ];

      render(<CollectionBadgeStack collections={collections} maxBadges={3} />);

      // Should show 3 badges
      expect(screen.getByText('One')).toBeInTheDocument();
      expect(screen.getByText('Two')).toBeInTheDocument();
      expect(screen.getByText('Three')).toBeInTheDocument();

      // Only 1 hidden
      expect(screen.getByText('+1 more...')).toBeInTheDocument();
    });

    it('does not show overflow badge when collections equal maxBadges', () => {
      const collections: CollectionInfo[] = [
        { id: '1', name: 'One', is_default: false },
        { id: '2', name: 'Two', is_default: false },
      ];

      render(<CollectionBadgeStack collections={collections} maxBadges={2} />);

      expect(screen.queryByText(/more\.\.\./)).not.toBeInTheDocument();
    });
  });

  // ============================================================================
  // Tooltip Tests
  // ============================================================================

  describe('Tooltip', () => {
    it('tooltip shows remaining collection names on hover', async () => {
      const user = userEvent.setup();
      render(<CollectionBadgeStack collections={mockCollections} />);

      const overflowBadge = screen.getByText('+2 more...');
      await user.hover(overflowBadge);

      // Hidden collections should appear in tooltip (Radix renders duplicates for a11y)
      const archiveElements = await screen.findAllByText('Archive');
      expect(archiveElements.length).toBeGreaterThan(0);

      const favoritesElements = screen.getAllByText('Favorites');
      expect(favoritesElements.length).toBeGreaterThan(0);
    });

    it('tooltip is accessible via keyboard (tab focus)', async () => {
      const user = userEvent.setup();
      render(<CollectionBadgeStack collections={mockCollections} />);

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
      render(<CollectionBadgeStack collections={twoCollections} />);

      const workBadge = screen.getByLabelText('In collection: Work');
      const personalBadge = screen.getByLabelText('In collection: Personal');

      expect(workBadge).toBeInTheDocument();
      expect(personalBadge).toBeInTheDocument();
    });

    it('overflow badge has aria-label listing hidden collections', () => {
      render(<CollectionBadgeStack collections={mockCollections} />);

      const overflowBadge = screen.getByLabelText('2 more collections: Archive, Favorites');
      expect(overflowBadge).toBeInTheDocument();
    });

    it('container has role="list" attribute', () => {
      render(<CollectionBadgeStack collections={singleCollection} />);

      const container = screen.getByRole('list');
      expect(container).toBeInTheDocument();
      expect(container).toHaveAttribute('aria-label', 'Collection memberships');
    });

    it('individual badges are wrapped in role="listitem"', () => {
      render(<CollectionBadgeStack collections={twoCollections} />);

      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(2);

      // Verify badges are within listitems
      expect(within(listItems[0]).getByText('Work')).toBeInTheDocument();
      expect(within(listItems[1]).getByText('Personal')).toBeInTheDocument();
    });

    it('overflow badge is also wrapped in role="listitem"', () => {
      render(<CollectionBadgeStack collections={mockCollections} />);

      const listItems = screen.getAllByRole('listitem');
      // 2 visible + 1 overflow
      expect(listItems).toHaveLength(3);

      // Last listitem should contain overflow badge
      expect(within(listItems[2]).getByText('+2 more...')).toBeInTheDocument();
    });

    it('badges are keyboard focusable', () => {
      render(<CollectionBadgeStack collections={singleCollection} />);

      const badge = screen.getByText('Work');
      expect(badge).toHaveAttribute('tabIndex', '0');
    });
  });

  // ============================================================================
  // Edge Cases
  // ============================================================================

  describe('Edge Cases', () => {
    it('handles null collections gracefully', () => {
      // @ts-expect-error - Testing runtime behavior with invalid input
      const { container } = render(<CollectionBadgeStack collections={null} />);
      expect(container.firstChild).toBeNull();
    });

    it('handles undefined collections gracefully', () => {
      // @ts-expect-error - Testing runtime behavior with invalid input
      const { container } = render(<CollectionBadgeStack collections={undefined} />);
      expect(container.firstChild).toBeNull();
    });

    it('handles collections with null items gracefully', () => {
      const collectionsWithNull = [
        { id: '1', name: 'Work', is_default: false },
        null,
        { id: '2', name: 'Personal', is_default: false },
      ] as CollectionInfo[];

      render(<CollectionBadgeStack collections={collectionsWithNull} />);

      expect(screen.getByText('Work')).toBeInTheDocument();
      expect(screen.getByText('Personal')).toBeInTheDocument();
    });

    it('handles empty collection names gracefully', () => {
      const collectionsWithEmpty: CollectionInfo[] = [
        { id: '1', name: '', is_default: false },
        { id: '2', name: 'Valid', is_default: false },
      ];

      render(<CollectionBadgeStack collections={collectionsWithEmpty} />);

      // Both should render (empty string is valid, just empty)
      expect(screen.getByText('Valid')).toBeInTheDocument();
    });

    it('handles long collection names with truncation', () => {
      const longNameCollection: CollectionInfo[] = [
        {
          id: '1',
          name: 'This is a very long collection name that should be truncated',
          is_default: false,
        },
      ];

      render(<CollectionBadgeStack collections={longNameCollection} />);

      const badge = screen.getByText(
        'This is a very long collection name that should be truncated'
      );
      expect(badge).toBeInTheDocument();
      // Badge should have truncate class for CSS truncation
      expect(badge).toHaveClass('truncate');
    });

    it('handles collections where is_default is undefined', () => {
      const collectionsWithUndefinedDefault: CollectionInfo[] = [
        { id: '1', name: 'Work' } as CollectionInfo, // is_default undefined
        { id: '2', name: 'Personal', is_default: false },
      ];

      render(<CollectionBadgeStack collections={collectionsWithUndefinedDefault} />);

      // Both should render (undefined is_default treated as non-default)
      expect(screen.getByText('Work')).toBeInTheDocument();
      expect(screen.getByText('Personal')).toBeInTheDocument();
    });

    it('handles maxBadges of 0', () => {
      render(<CollectionBadgeStack collections={twoCollections} maxBadges={0} />);

      // All should be in overflow
      expect(screen.queryByText('Work')).not.toBeInTheDocument();
      expect(screen.queryByText('Personal')).not.toBeInTheDocument();
      expect(screen.getByText('+2 more...')).toBeInTheDocument();
    });

    it('handles maxBadges of 1', () => {
      render(<CollectionBadgeStack collections={twoCollections} maxBadges={1} />);

      expect(screen.getByText('Work')).toBeInTheDocument();
      expect(screen.queryByText('Personal')).not.toBeInTheDocument();
      expect(screen.getByText('+1 more...')).toBeInTheDocument();
    });
  });

  // ============================================================================
  // Custom Styling Tests
  // ============================================================================

  describe('Custom Styling', () => {
    it('applies custom className to container', () => {
      render(<CollectionBadgeStack collections={singleCollection} className="custom-class" />);

      const container = screen.getByRole('list');
      expect(container).toHaveClass('custom-class');
    });

    it('preserves default classes when custom className is added', () => {
      render(<CollectionBadgeStack collections={singleCollection} className="custom-class" />);

      const container = screen.getByRole('list');
      expect(container).toHaveClass('inline-flex');
      expect(container).toHaveClass('custom-class');
    });
  });
});
