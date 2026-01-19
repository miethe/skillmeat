/**
 * @jest-environment jsdom
 *
 * TagBadge Component Tests
 *
 * Tests for the TagBadge component which displays tags as colored badges
 * with overflow handling and "+n more" tooltip functionality.
 *
 * Note: Radix Tooltip hover tests are skipped as they can be flaky in jsdom.
 * Tooltip behavior is better tested in E2E tests.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TagBadge } from '@/components/marketplace/tag-badge';

describe('TagBadge', () => {
  describe('Rendering', () => {
    it('renders tag text correctly', () => {
      render(<TagBadge tags={['python', 'testing', 'automation']} />);

      expect(screen.getByText('python')).toBeInTheDocument();
      expect(screen.getByText('testing')).toBeInTheDocument();
      expect(screen.getByText('automation')).toBeInTheDocument();
    });

    it('renders nothing when tags array is empty', () => {
      const { container } = render(<TagBadge tags={[]} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders nothing when tags is undefined', () => {
      // @ts-expect-error Testing undefined case
      const { container } = render(<TagBadge tags={undefined} />);

      expect(container.firstChild).toBeNull();
    });

    it('renders single tag correctly', () => {
      render(<TagBadge tags={['single']} />);

      expect(screen.getByText('single')).toBeInTheDocument();
    });

    it('applies custom className to container', () => {
      render(<TagBadge tags={['test']} className="custom-class" />);

      const container = screen.getByRole('list', { name: 'Tags' });
      expect(container).toHaveClass('custom-class');
    });
  });

  describe('Overflow Handling', () => {
    it('shows only maxDisplay tags by default (3)', () => {
      render(<TagBadge tags={['one', 'two', 'three', 'four', 'five']} />);

      expect(screen.getByText('one')).toBeInTheDocument();
      expect(screen.getByText('two')).toBeInTheDocument();
      expect(screen.getByText('three')).toBeInTheDocument();
      expect(screen.getByText('+2 more')).toBeInTheDocument();
      expect(screen.queryByText('four')).not.toBeInTheDocument();
      expect(screen.queryByText('five')).not.toBeInTheDocument();
    });

    it('respects custom maxDisplay value', () => {
      render(<TagBadge tags={['one', 'two', 'three', 'four', 'five']} maxDisplay={2} />);

      expect(screen.getByText('one')).toBeInTheDocument();
      expect(screen.getByText('two')).toBeInTheDocument();
      expect(screen.getByText('+3 more')).toBeInTheDocument();
      expect(screen.queryByText('three')).not.toBeInTheDocument();
    });

    it('does not show overflow badge when tags fit within maxDisplay', () => {
      render(<TagBadge tags={['one', 'two']} maxDisplay={3} />);

      expect(screen.getByText('one')).toBeInTheDocument();
      expect(screen.getByText('two')).toBeInTheDocument();
      expect(screen.queryByText(/more/)).not.toBeInTheDocument();
    });

    it('overflow badge indicates count of hidden tags', () => {
      render(<TagBadge tags={['one', 'two', 'three', 'four', 'five', 'six']} maxDisplay={3} />);

      expect(screen.getByText('+3 more')).toBeInTheDocument();
    });
  });

  describe('Click Events', () => {
    it('calls onTagClick when a visible tag is clicked', async () => {
      const user = userEvent.setup();
      const handleTagClick = jest.fn();

      render(<TagBadge tags={['python', 'testing']} onTagClick={handleTagClick} />);

      await user.click(screen.getByText('python'));

      expect(handleTagClick).toHaveBeenCalledWith('python');
      expect(handleTagClick).toHaveBeenCalledTimes(1);
    });

    it('does not call onTagClick when onTagClick is not provided', async () => {
      const user = userEvent.setup();

      render(<TagBadge tags={['python']} />);

      // Should not throw when clicking
      await user.click(screen.getByText('python'));
    });

    it('stops event propagation when tag is clicked', async () => {
      const user = userEvent.setup();
      const parentClick = jest.fn();
      const tagClick = jest.fn();

      render(
        <div onClick={parentClick}>
          <TagBadge tags={['python']} onTagClick={tagClick} />
        </div>
      );

      await user.click(screen.getByText('python'));

      expect(tagClick).toHaveBeenCalled();
      expect(parentClick).not.toHaveBeenCalled();
    });

    it('calls onClick for each distinct tag', async () => {
      const user = userEvent.setup();
      const handleTagClick = jest.fn();

      render(<TagBadge tags={['python', 'testing', 'ci']} onTagClick={handleTagClick} />);

      await user.click(screen.getByText('python'));
      await user.click(screen.getByText('testing'));
      await user.click(screen.getByText('ci'));

      expect(handleTagClick).toHaveBeenCalledTimes(3);
      expect(handleTagClick).toHaveBeenNthCalledWith(1, 'python');
      expect(handleTagClick).toHaveBeenNthCalledWith(2, 'testing');
      expect(handleTagClick).toHaveBeenNthCalledWith(3, 'ci');
    });
  });

  describe('Keyboard Navigation', () => {
    it('allows tag activation with Enter key', async () => {
      const user = userEvent.setup();
      const handleTagClick = jest.fn();

      render(<TagBadge tags={['python']} onTagClick={handleTagClick} />);

      const tag = screen.getByText('python');
      tag.focus();
      await user.keyboard('{Enter}');

      expect(handleTagClick).toHaveBeenCalledWith('python');
    });

    it('allows tag activation with Space key', async () => {
      const user = userEvent.setup();
      const handleTagClick = jest.fn();

      render(<TagBadge tags={['python']} onTagClick={handleTagClick} />);

      const tag = screen.getByText('python');
      tag.focus();
      await user.keyboard(' ');

      expect(handleTagClick).toHaveBeenCalledWith('python');
    });

    it('makes clickable tags focusable', () => {
      render(<TagBadge tags={['python']} onTagClick={jest.fn()} />);

      const tag = screen.getByText('python');
      expect(tag).toHaveAttribute('tabindex', '0');
    });

    it('does not make non-clickable tags focusable', () => {
      render(<TagBadge tags={['python']} />);

      const tag = screen.getByText('python');
      expect(tag).not.toHaveAttribute('tabindex');
    });
  });

  describe('Accessibility', () => {
    it('has proper ARIA label for filter action when clickable', () => {
      render(<TagBadge tags={['python']} onTagClick={jest.fn()} />);

      expect(screen.getByRole('button', { name: 'Filter by tag: python' })).toBeInTheDocument();
    });

    it('has proper ARIA label for display only when not clickable', () => {
      render(<TagBadge tags={['python']} />);

      expect(screen.getByLabelText('Tag: python')).toBeInTheDocument();
    });

    it('has role="list" on container', () => {
      render(<TagBadge tags={['python']} />);

      expect(screen.getByRole('list', { name: 'Tags' })).toBeInTheDocument();
    });

    it('has role="listitem" on each tag wrapper', () => {
      render(<TagBadge tags={['python', 'testing']} />);

      const listItems = screen.getAllByRole('listitem');
      expect(listItems).toHaveLength(2);
    });

    it('overflow badge has descriptive aria-label', () => {
      render(<TagBadge tags={['one', 'two', 'three', 'four', 'five']} maxDisplay={3} />);

      expect(screen.getByLabelText('2 more tags: four, five')).toBeInTheDocument();
    });

    it('clickable tags have role="button"', () => {
      render(<TagBadge tags={['python', 'testing']} onTagClick={jest.fn()} />);

      expect(screen.getByRole('button', { name: 'Filter by tag: python' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Filter by tag: testing' })).toBeInTheDocument();
    });
  });

  describe('Visual Styling', () => {
    it('applies hover effect classes to clickable tags', () => {
      render(<TagBadge tags={['python']} onTagClick={jest.fn()} />);

      const tag = screen.getByText('python');
      expect(tag).toHaveClass('cursor-pointer');
      expect(tag).toHaveClass('hover:opacity-80');
    });

    it('does not apply hover effect classes to non-clickable tags', () => {
      render(<TagBadge tags={['python']} />);

      const tag = screen.getByText('python');
      expect(tag).not.toHaveClass('cursor-pointer');
    });
  });

  describe('Edge Cases', () => {
    it('handles very long tag names', () => {
      const longTag = 'this-is-a-very-long-tag-name-that-might-overflow';
      render(<TagBadge tags={[longTag]} />);

      expect(screen.getByText(longTag)).toBeInTheDocument();
    });

    it('handles special characters in tags', () => {
      render(<TagBadge tags={['c++', 'c#', 'node.js']} />);

      expect(screen.getByText('c++')).toBeInTheDocument();
      expect(screen.getByText('c#')).toBeInTheDocument();
      expect(screen.getByText('node.js')).toBeInTheDocument();
    });

    it('handles numeric tags', () => {
      render(<TagBadge tags={['v1.0.0', '2024', 'beta-3']} />);

      expect(screen.getByText('v1.0.0')).toBeInTheDocument();
      expect(screen.getByText('2024')).toBeInTheDocument();
      expect(screen.getByText('beta-3')).toBeInTheDocument();
    });

    it('handles maxDisplay of 0', () => {
      render(<TagBadge tags={['one', 'two', 'three']} maxDisplay={0} />);

      expect(screen.getByText('+3 more')).toBeInTheDocument();
      expect(screen.queryByText('one')).not.toBeInTheDocument();
    });

    it('handles maxDisplay larger than tags array', () => {
      render(<TagBadge tags={['one', 'two']} maxDisplay={10} />);

      expect(screen.getByText('one')).toBeInTheDocument();
      expect(screen.getByText('two')).toBeInTheDocument();
      expect(screen.queryByText(/more/)).not.toBeInTheDocument();
    });
  });

  describe('Color Consistency', () => {
    it('assigns consistent colors to the same tag', () => {
      const { rerender } = render(<TagBadge tags={['python']} />);

      const firstRender = screen.getByText('python');
      const firstStyle = firstRender.getAttribute('style');

      rerender(<TagBadge tags={['python']} />);

      const secondRender = screen.getByText('python');
      const secondStyle = secondRender.getAttribute('style');

      expect(firstStyle).toBe(secondStyle);
    });
  });
});
