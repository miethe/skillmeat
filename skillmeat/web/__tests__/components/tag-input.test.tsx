/**
 * @jest-environment jsdom
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TagInput, type Tag } from '@/components/ui/tag-input';

describe('TagInput', () => {
  const mockTags: Tag[] = [
    { id: '1', name: 'React', slug: 'react', color: '#61DAFB' },
    { id: '2', name: 'TypeScript', slug: 'typescript', color: '#3178C6' },
    { id: '3', name: 'Python', slug: 'python', color: '#3776AB' },
    { id: '4', name: 'JavaScript', slug: 'javascript', color: '#F7DF1E' },
    { id: '5', name: 'Node.js', slug: 'nodejs', color: '#339933' },
  ];

  const defaultProps = {
    value: [],
    onChange: jest.fn(),
    suggestions: mockTags,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders with placeholder when empty', () => {
      render(<TagInput {...defaultProps} placeholder="Add tags..." />);
      expect(screen.getByPlaceholderText('Add tags...')).toBeInTheDocument();
    });

    it('renders without placeholder when tags exist', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} placeholder="Add tags..." />);

      const input = screen.getByRole('combobox');
      expect(input).toHaveAttribute('placeholder', '');
    });

    it('displays existing tags as badges', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} />);

      expect(screen.getByText('React')).toBeInTheDocument();
      expect(screen.getByText('TypeScript')).toBeInTheDocument();
    });

    it('displays tag names when tag IDs provided', () => {
      render(<TagInput {...defaultProps} value={['1']} />);
      expect(screen.getByText('React')).toBeInTheDocument();
    });

    it('displays raw string when tag not in suggestions', () => {
      render(<TagInput {...defaultProps} value={['custom-tag']} />);
      expect(screen.getByText('custom-tag')).toBeInTheDocument();
    });

    it('renders remove buttons for each tag when not disabled', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} />);

      const removeButtons = screen.getAllByLabelText(/Remove tag/i);
      expect(removeButtons).toHaveLength(2);
    });

    it('does not render remove buttons when disabled', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} disabled />);

      const removeButtons = screen.queryAllByLabelText(/Remove tag/i);
      expect(removeButtons).toHaveLength(0);
    });
  });

  describe('Suggestions', () => {
    it('shows suggestions when typing', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'py');

      await waitFor(() => {
        expect(screen.getByText('Python')).toBeInTheDocument();
      });
    });

    it('filters suggestions by name', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'react');

      await waitFor(() => {
        expect(screen.getByText('React')).toBeInTheDocument();
        expect(screen.queryByText('Python')).not.toBeInTheDocument();
      });
    });

    it('filters suggestions by slug', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'nodejs');

      await waitFor(() => {
        expect(screen.getByText('Node.js')).toBeInTheDocument();
      });
    });

    it('does not show already selected tags in suggestions', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} value={['1']} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'r');

      await waitFor(() => {
        expect(screen.queryByRole('option', { name: /React/i })).not.toBeInTheDocument();
      });
    });

    it('shows suggestions on focus if input has value', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'py');

      // Blur to close suggestions
      await user.click(document.body);
      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      });

      // Focus again
      await user.click(input);

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });
    });

    it('limits suggestions to 10 items', async () => {
      const user = userEvent.setup();
      const manySuggestions: Tag[] = Array.from({ length: 20 }, (_, i) => ({
        id: `${i + 1}`,
        name: `Tag ${i + 1}`,
        slug: `tag-${i + 1}`,
      }));

      render(<TagInput {...defaultProps} suggestions={manySuggestions} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'tag');

      await waitFor(() => {
        const options = screen.getAllByRole('option');
        expect(options).toHaveLength(10);
      });
    });

    it('calls onSearch when input changes', async () => {
      const user = userEvent.setup();
      const onSearch = jest.fn();
      render(<TagInput {...defaultProps} onSearch={onSearch} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'test');

      expect(onSearch).toHaveBeenCalledWith('test');
    });

    it('displays tag colors in suggestions', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'python');

      await waitFor(() => {
        const badge = screen.getByText('Python').closest('.badge');
        expect(badge).toBeInTheDocument();
      });
    });
  });

  describe('Adding Tags', () => {
    it('adds tag on Enter key', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'new-tag{Enter}');

      expect(onChange).toHaveBeenCalledWith(['new-tag']);
    });

    it('adds tag from suggestion on Enter key', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'py');

      await waitFor(() => {
        expect(screen.getByText('Python')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}{Enter}');

      expect(onChange).toHaveBeenCalledWith(['3']); // Python's ID
    });

    it('adds tag when clicking suggestion', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'react');

      await waitFor(() => {
        expect(screen.getByText('React')).toBeInTheDocument();
      });

      const suggestion = screen.getByText('React');
      await user.click(suggestion);

      expect(onChange).toHaveBeenCalledWith(['1']); // React's ID
    });

    it('clears input after adding tag', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox') as HTMLInputElement;
      await user.type(input, 'test{Enter}');

      await waitFor(() => {
        expect(input.value).toBe('');
      });
    });

    it('closes suggestions after adding tag', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'react');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}{Enter}');

      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      });
    });

    it('does not add duplicate tags', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} value={['1']} onChange={onChange} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'react{Enter}');

      // onChange should not be called since tag already exists
      expect(onChange).not.toHaveBeenCalled();
    });

    it('does not add empty tags', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} />);

      const input = screen.getByRole('combobox');
      await user.type(input, '   {Enter}');

      expect(onChange).not.toHaveBeenCalled();
    });

    it('respects allowCreate=false', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} allowCreate={false} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'new-tag{Enter}');

      // Should not add tag when allowCreate is false
      expect(onChange).not.toHaveBeenCalled();
    });

    it('allows creating new tag when allowCreate=true and no suggestions highlighted', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} allowCreate={true} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'custom-tag{Enter}');

      expect(onChange).toHaveBeenCalledWith(['custom-tag']);
    });
  });

  describe('Removing Tags', () => {
    it('removes tag when clicking X button', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} value={['1', '2']} onChange={onChange} />);

      const removeButtons = screen.getAllByLabelText(/Remove tag/i);
      await user.click(removeButtons[0]);

      expect(onChange).toHaveBeenCalledWith(['2']); // First tag removed
    });

    it('removes last tag on Backspace when input is empty', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} value={['1', '2']} onChange={onChange} />);

      const input = screen.getByRole('combobox');
      await user.click(input);
      await user.keyboard('{Backspace}');

      expect(onChange).toHaveBeenCalledWith(['1']); // Last tag removed
    });

    it('does not remove tag on Backspace when input has text', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} value={['1', '2']} onChange={onChange} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'test{Backspace}');

      // onChange should not be called for tag removal
      expect(onChange).not.toHaveBeenCalled();
    });

    it('focuses input after removing tag', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} value={['1']} />);

      const removeButton = screen.getByLabelText(/Remove tag/i);
      await user.click(removeButton);

      const input = screen.getByRole('combobox');
      expect(input).toHaveFocus();
    });
  });

  describe('Keyboard Navigation', () => {
    it('navigates suggestions with ArrowDown', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'r');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}');

      const firstOption = screen.getAllByRole('option')[0];
      expect(firstOption).toHaveAttribute('aria-selected', 'true');
    });

    it('navigates suggestions with ArrowUp', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'j');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}{ArrowDown}{ArrowUp}');

      const firstOption = screen.getAllByRole('option')[0];
      expect(firstOption).toHaveAttribute('aria-selected', 'true');
    });

    it('does not go above first suggestion', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'j');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowUp}');

      // No option should be selected
      const options = screen.getAllByRole('option');
      options.forEach(option => {
        expect(option).not.toHaveAttribute('aria-selected', 'true');
      });
    });

    it('does not go below last suggestion', async () => {
      const user = userEvent.setup();
      const limitedSuggestions = mockTags.slice(0, 2);
      render(<TagInput {...defaultProps} suggestions={limitedSuggestions} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 't');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}{ArrowDown}{ArrowDown}');

      const lastOption = screen.getAllByRole('option')[1];
      expect(lastOption).toHaveAttribute('aria-selected', 'true');
    });

    it('closes suggestions on Escape', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'react');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{Escape}');

      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      });
    });

    it('resets highlighted index on Escape', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'r');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}{Escape}');

      // When reopening, no option should be highlighted
      await user.type(input, 'a');
      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      const options = screen.getAllByRole('option');
      options.forEach(option => {
        expect(option).not.toHaveAttribute('aria-selected', 'true');
      });
    });
  });

  describe('CSV Paste', () => {
    it('handles CSV paste with multiple tags', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} allowCreate={true} />);

      const input = screen.getByRole('combobox');
      await user.click(input);

      const pasteEvent = new ClipboardEvent('paste', {
        clipboardData: new DataTransfer(),
      });
      pasteEvent.clipboardData?.setData('text', 'tag1, tag2, tag3');

      fireEvent(input, pasteEvent);

      // Should add all three tags (called 3 times)
      await waitFor(() => {
        expect(onChange).toHaveBeenCalled();
      });
    });

    it('trims whitespace from pasted tags', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} allowCreate={true} />);

      const input = screen.getByRole('combobox');
      await user.click(input);

      const pasteEvent = new ClipboardEvent('paste', {
        clipboardData: new DataTransfer(),
      });
      pasteEvent.clipboardData?.setData('text', '  tag1  ,  tag2  ');

      fireEvent(input, pasteEvent);

      await waitFor(() => {
        expect(onChange).toHaveBeenCalled();
      });
    });

    it('ignores empty tags in CSV paste', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} onChange={onChange} allowCreate={true} />);

      const input = screen.getByRole('combobox');
      await user.click(input);

      const pasteEvent = new ClipboardEvent('paste', {
        clipboardData: new DataTransfer(),
      });
      pasteEvent.clipboardData?.setData('text', 'tag1, , tag2, ,');

      fireEvent(input, pasteEvent);

      await waitFor(() => {
        expect(onChange).toHaveBeenCalled();
      });
      // Should only add tag1 and tag2 (not empty values)
    });

    it('does not interfere with non-CSV paste', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox') as HTMLInputElement;
      await user.click(input);
      await user.paste('single-tag');

      // Input should contain the pasted text
      expect(input.value).toBe('single-tag');
    });
  });

  describe('Max Tags Limit', () => {
    it('disables input when max tags reached', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} maxTags={2} />);

      const input = screen.getByRole('combobox');
      expect(input).toBeDisabled();
    });

    it('shows max tags message when limit reached', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} maxTags={2} />);

      expect(screen.getByText(/Maximum 2 tags reached/i)).toBeInTheDocument();
    });

    it('does not add tag when max tags reached', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} value={['1', '2']} onChange={onChange} maxTags={2} />);

      // Input is disabled, so typing should not work
      const input = screen.getByRole('combobox');
      expect(input).toBeDisabled();
    });

    it('respects max tags limit during CSV paste', async () => {
      const user = userEvent.setup();
      const onChange = jest.fn();
      render(<TagInput {...defaultProps} value={['1']} onChange={onChange} maxTags={2} allowCreate={true} />);

      const input = screen.getByRole('combobox');
      await user.click(input);

      const pasteEvent = new ClipboardEvent('paste', {
        clipboardData: new DataTransfer(),
      });
      pasteEvent.clipboardData?.setData('text', 'tag2, tag3, tag4');

      fireEvent(input, pasteEvent);

      // Should only add one more tag (to reach maxTags=2)
      await waitFor(() => {
        expect(onChange).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility', () => {
    it('has combobox role on input', () => {
      render(<TagInput {...defaultProps} />);
      expect(screen.getByRole('combobox')).toBeInTheDocument();
    });

    it('has listbox role on suggestions dropdown', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'r');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });
    });

    it('sets aria-expanded correctly', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      expect(input).toHaveAttribute('aria-expanded', 'false');

      await user.type(input, 'r');

      await waitFor(() => {
        expect(input).toHaveAttribute('aria-expanded', 'true');
      });
    });

    it('sets aria-controls on input', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      expect(input).toHaveAttribute('aria-controls', 'tag-suggestions');
    });

    it('sets aria-activedescendant for highlighted option', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      await user.type(input, 'r');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      await user.keyboard('{ArrowDown}');

      expect(input).toHaveAttribute('aria-activedescendant', 'tag-suggestion-0');
    });

    it('has proper aria-label on input', () => {
      render(<TagInput {...defaultProps} />);

      const input = screen.getByRole('combobox');
      expect(input).toHaveAttribute('aria-label', 'Tag input');
    });

    it('has aria-label on remove buttons', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} />);

      expect(screen.getByLabelText('Remove tag React')).toBeInTheDocument();
      expect(screen.getByLabelText('Remove tag TypeScript')).toBeInTheDocument();
    });

    it('shows status message for max tags with aria-live', () => {
      render(<TagInput {...defaultProps} value={['1', '2']} maxTags={2} />);

      const status = screen.getByRole('status');
      expect(status).toHaveAttribute('aria-live', 'polite');
      expect(status).toHaveTextContent('Maximum 2 tags reached');
    });
  });

  describe('Disabled State', () => {
    it('disables input when disabled prop is true', () => {
      render(<TagInput {...defaultProps} disabled />);

      const input = screen.getByRole('combobox');
      expect(input).toBeDisabled();
    });

    it('does not show suggestions when disabled', async () => {
      const user = userEvent.setup();
      render(<TagInput {...defaultProps} disabled />);

      const input = screen.getByRole('combobox');

      // Clicking disabled input should not open suggestions
      await user.click(input);

      expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
    });

    it('applies opacity styling when disabled', () => {
      const { container } = render(<TagInput {...defaultProps} disabled />);

      const wrapper = container.querySelector('.opacity-50');
      expect(wrapper).toBeInTheDocument();
    });
  });

  describe('Click Outside', () => {
    it('closes suggestions when clicking outside', async () => {
      const user = userEvent.setup();
      render(
        <div>
          <TagInput {...defaultProps} />
          <button>Outside</button>
        </div>
      );

      const input = screen.getByRole('combobox');
      await user.type(input, 'r');

      await waitFor(() => {
        expect(screen.getByRole('listbox')).toBeInTheDocument();
      });

      const outsideButton = screen.getByText('Outside');
      await user.click(outsideButton);

      await waitFor(() => {
        expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
      });
    });
  });

  describe('Custom CSS Classes', () => {
    it('applies custom className to container', () => {
      const { container } = render(<TagInput {...defaultProps} className="custom-class" />);

      const wrapper = container.querySelector('.custom-class');
      expect(wrapper).toBeInTheDocument();
    });
  });
});
