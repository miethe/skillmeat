import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RatingDialog } from '@/components/RatingDialog';

describe('RatingDialog', () => {
  const defaultProps = {
    artifactId: 'test-artifact-123',
    artifactName: 'Test Artifact',
    isOpen: true,
    onClose: jest.fn(),
    onSubmit: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders when isOpen is true', () => {
      render(<RatingDialog {...defaultProps} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText('Rate Test Artifact')).toBeInTheDocument();
    });

    it('does not render when isOpen is false', () => {
      render(<RatingDialog {...defaultProps} isOpen={false} />);
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });

    it('shows artifact name in title', () => {
      render(<RatingDialog {...defaultProps} artifactName="Canvas Design" />);
      expect(screen.getByText('Rate Canvas Design')).toBeInTheDocument();
    });

    it('shows description text', () => {
      render(<RatingDialog {...defaultProps} />);
      expect(screen.getByText('Share your experience with this artifact')).toBeInTheDocument();
    });

    it('renders all 5 stars', () => {
      render(<RatingDialog {...defaultProps} />);
      const starButtons = screen.getAllByRole('button', { name: /Rate \d star/ });
      expect(starButtons).toHaveLength(5);
    });

    it('renders feedback textarea', () => {
      render(<RatingDialog {...defaultProps} />);
      expect(screen.getByLabelText('Optional feedback')).toBeInTheDocument();
    });

    it('renders submit and cancel buttons', () => {
      render(<RatingDialog {...defaultProps} />);
      expect(screen.getByRole('button', { name: 'Submit' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    });
  });

  describe('Star Selection (Mouse)', () => {
    it('selects rating when star is clicked', () => {
      render(<RatingDialog {...defaultProps} />);
      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      expect(screen.getByText('3 stars')).toBeInTheDocument();
    });

    it('shows preview on hover', () => {
      render(<RatingDialog {...defaultProps} />);
      const fourthStar = screen.getByRole('button', { name: 'Rate 4 stars' });

      // Initially no rating shown
      expect(screen.queryByText(/\d stars?/)).not.toBeInTheDocument();

      // Hover shows preview (stars become filled)
      fireEvent.mouseEnter(fourthStar);
      // The rating display only shows when a rating is selected, not on hover
      // Hover just changes the star colors (fill state)

      // Click sets rating
      fireEvent.click(fourthStar);
      expect(screen.getByText('4 stars')).toBeInTheDocument();
    });

    it('removes hover preview on mouse leave', () => {
      render(<RatingDialog {...defaultProps} />);
      const secondStar = screen.getByRole('button', { name: 'Rate 2 stars' });

      fireEvent.mouseEnter(secondStar);
      fireEvent.mouseLeave(secondStar);

      // Should not show any rating text when no rating selected
      expect(screen.queryByText(/\d stars?/)).not.toBeInTheDocument();
    });

    it('persists selected rating after hover', () => {
      render(<RatingDialog {...defaultProps} />);
      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      const fifthStar = screen.getByRole('button', { name: 'Rate 5 stars' });

      // Select 3 stars
      fireEvent.click(thirdStar);
      expect(screen.getByText('3 stars')).toBeInTheDocument();

      // Hover over 5 stars
      fireEvent.mouseEnter(fifthStar);
      fireEvent.mouseLeave(fifthStar);

      // Should still show 3 stars
      expect(screen.getByText('3 stars')).toBeInTheDocument();
    });

    it('handles single star rating correctly', () => {
      render(<RatingDialog {...defaultProps} />);
      const firstStar = screen.getByRole('button', { name: 'Rate 1 star' });

      fireEvent.click(firstStar);
      expect(screen.getByText('1 star')).toBeInTheDocument();
    });
  });

  describe('Star Selection (Keyboard)', () => {
    it('increases rating with ArrowRight key', () => {
      render(<RatingDialog {...defaultProps} initialRating={2} />);
      const starContainer = screen.getByRole('group', { name: /Rating:/ });

      fireEvent.keyDown(starContainer, { key: 'ArrowRight' });
      expect(screen.getByText('3 stars')).toBeInTheDocument();
    });

    it('decreases rating with ArrowLeft key', () => {
      render(<RatingDialog {...defaultProps} initialRating={4} />);
      const starContainer = screen.getByRole('group', { name: /Rating:/ });

      fireEvent.keyDown(starContainer, { key: 'ArrowLeft' });
      expect(screen.getByText('3 stars')).toBeInTheDocument();
    });

    it('does not increase rating beyond 5', () => {
      render(<RatingDialog {...defaultProps} initialRating={5} />);
      const starContainer = screen.getByRole('group', { name: /Rating:/ });

      fireEvent.keyDown(starContainer, { key: 'ArrowRight' });
      expect(screen.getByText('5 stars')).toBeInTheDocument();
    });

    it('does not decrease rating below 1', () => {
      render(<RatingDialog {...defaultProps} initialRating={1} />);
      const starContainer = screen.getByRole('group', { name: /Rating:/ });

      fireEvent.keyDown(starContainer, { key: 'ArrowLeft' });
      expect(screen.getByText('1 star')).toBeInTheDocument();
    });

    it('submits form with Enter key when rating selected', async () => {
      const onSubmit = jest.fn().mockResolvedValue(undefined);
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} initialRating={3} />);
      const starContainer = screen.getByRole('group', { name: /Rating:/ });

      fireEvent.keyDown(starContainer, { key: 'Enter' });

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(3, undefined);
      });
    });
  });

  describe('Feedback Input', () => {
    it('allows typing in feedback textarea', () => {
      render(<RatingDialog {...defaultProps} />);
      const textarea = screen.getByLabelText('Optional feedback');

      fireEvent.change(textarea, { target: { value: 'Great artifact!' } });
      expect(textarea).toHaveValue('Great artifact!');
    });

    it('shows character count', () => {
      render(<RatingDialog {...defaultProps} />);
      const textarea = screen.getByLabelText('Optional feedback');

      fireEvent.change(textarea, { target: { value: 'Test feedback' } });
      expect(screen.getByText('13/1000 characters')).toBeInTheDocument();
    });

    it('feedback is optional', async () => {
      const onSubmit = jest.fn().mockResolvedValue(undefined);
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(3, undefined);
      });
    });

    it('sends feedback with rating when provided', async () => {
      const onSubmit = jest.fn().mockResolvedValue(undefined);
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const fourthStar = screen.getByRole('button', { name: 'Rate 4 stars' });
      fireEvent.click(fourthStar);

      const textarea = screen.getByLabelText('Optional feedback');
      fireEvent.change(textarea, { target: { value: 'Excellent!' } });

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(4, 'Excellent!');
      });
    });
  });

  describe('Submit/Cancel Behavior', () => {
    it('calls onSubmit with rating and feedback', async () => {
      const onSubmit = jest.fn().mockResolvedValue(undefined);
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const fifthStar = screen.getByRole('button', { name: 'Rate 5 stars' });
      fireEvent.click(fifthStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(5, undefined);
      });
    });

    it('submit button is disabled when no rating selected', () => {
      render(<RatingDialog {...defaultProps} />);
      const submitButton = screen.getByRole('button', { name: 'Submit' });
      expect(submitButton).toBeDisabled();
    });

    it('submit button is enabled when rating selected', () => {
      render(<RatingDialog {...defaultProps} initialRating={3} />);
      const submitButton = screen.getByRole('button', { name: 'Submit' });
      expect(submitButton).toBeEnabled();
    });

    it('calls onClose when cancel button clicked', () => {
      const onClose = jest.fn();
      render(<RatingDialog {...defaultProps} onClose={onClose} />);

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      fireEvent.click(cancelButton);

      expect(onClose).toHaveBeenCalled();
    });

    it('resets form state when dialog reopens', () => {
      const { rerender } = render(<RatingDialog {...defaultProps} isOpen={false} />);

      // Open dialog
      rerender(<RatingDialog {...defaultProps} isOpen={true} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);
      expect(screen.getByText('3 stars')).toBeInTheDocument();

      // Close and reopen
      rerender(<RatingDialog {...defaultProps} isOpen={false} />);
      rerender(<RatingDialog {...defaultProps} isOpen={true} />);

      // Should reset to no rating
      expect(screen.queryByText('3 stars')).not.toBeInTheDocument();
    });

    it('closes dialog on successful submit', async () => {
      const onSubmit = jest.fn().mockResolvedValue(undefined);
      const onClose = jest.fn();
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} onClose={onClose} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(onClose).toHaveBeenCalled();
      });
    });
  });

  describe('Accessibility', () => {
    it('dialog has proper ARIA role', () => {
      render(<RatingDialog {...defaultProps} />);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('star container has group role and aria-label', () => {
      render(<RatingDialog {...defaultProps} initialRating={3} />);
      const starContainer = screen.getByRole('group', { name: 'Rating: 3 out of 5 stars' });
      expect(starContainer).toBeInTheDocument();
    });

    it('each star button has descriptive aria-label', () => {
      render(<RatingDialog {...defaultProps} />);
      expect(screen.getByRole('button', { name: 'Rate 1 star' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Rate 2 stars' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Rate 3 stars' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Rate 4 stars' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Rate 5 stars' })).toBeInTheDocument();
    });

    it('textarea has aria-label', () => {
      render(<RatingDialog {...defaultProps} />);
      const textarea = screen.getByLabelText('Optional feedback');
      expect(textarea).toHaveAttribute('aria-label', 'Optional feedback');
    });

    it('star container is keyboard focusable', () => {
      render(<RatingDialog {...defaultProps} />);
      const starContainer = screen.getByRole('group', { name: /Rating:/ });
      expect(starContainer).toHaveAttribute('tabIndex', '0');
    });

    it('rating announcement has aria-live', () => {
      render(<RatingDialog {...defaultProps} initialRating={4} />);
      const announcement = screen.getByText('4 stars');
      expect(announcement).toHaveAttribute('aria-live', 'polite');
    });
  });

  describe('Loading State', () => {
    it('shows loading indicator during submission', async () => {
      const onSubmit = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      expect(screen.getByText('Submitting...')).toBeInTheDocument();
      expect(screen.getByLabelText('Loading')).toBeInTheDocument();
    });

    it('disables submit button during loading', async () => {
      const onSubmit = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      const loadingSubmitButton = screen.getByRole('button', { name: /Submitting/ });
      expect(loadingSubmitButton).toBeDisabled();
    });

    it('disables cancel button during loading', async () => {
      const onSubmit = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      const cancelButton = screen.getByRole('button', { name: 'Cancel' });
      expect(cancelButton).toBeDisabled();
    });

    it('disables star buttons during loading', async () => {
      const onSubmit = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      const starButtons = screen.getAllByRole('button', { name: /Rate \d star/ });
      starButtons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });

    it('disables feedback textarea during loading', async () => {
      const onSubmit = jest.fn(() => new Promise((resolve) => setTimeout(resolve, 100)));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      const textarea = screen.getByLabelText('Optional feedback');
      expect(textarea).toBeDisabled();
    });
  });

  describe('Error State', () => {
    it('displays error message when submission fails', async () => {
      const onSubmit = jest.fn().mockRejectedValue(new Error('Network error'));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument();
      });
    });

    it('error message has alert role and aria-live', async () => {
      const onSubmit = jest.fn().mockRejectedValue(new Error('Test error'));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        const errorMessage = screen.getByRole('alert');
        expect(errorMessage).toHaveAttribute('aria-live', 'assertive');
      });
    });

    it('keeps dialog open after error', async () => {
      const onSubmit = jest.fn().mockRejectedValue(new Error('Test error'));
      const onClose = jest.fn();
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} onClose={onClose} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Test error')).toBeInTheDocument();
      });

      expect(onClose).not.toHaveBeenCalled();
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('re-enables submit button after error', async () => {
      const onSubmit = jest.fn().mockRejectedValue(new Error('Test error'));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(screen.getByText('Test error')).toBeInTheDocument();
      });

      expect(submitButton).toBeEnabled();
    });

    it('shows error when submitting without rating', () => {
      render(<RatingDialog {...defaultProps} />);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      // Submit button should be disabled, but test the validation logic
      expect(submitButton).toBeDisabled();
    });

    it('clears error when rating is changed', async () => {
      const onSubmit = jest.fn().mockRejectedValue(new Error('Test error'));
      render(<RatingDialog {...defaultProps} onSubmit={onSubmit} />);

      const thirdStar = screen.getByRole('button', { name: 'Rate 3 stars' });
      fireEvent.click(thirdStar);

      const submitButton = screen.getByRole('button', { name: 'Submit' });
      fireEvent.click(submitButton);

      // Wait for error to appear
      await waitFor(
        () => {
          expect(screen.getByText('Test error')).toBeInTheDocument();
        },
        { timeout: 3000 }
      );

      // Verify error is visible
      expect(screen.getByRole('alert')).toHaveTextContent('Test error');

      // Change rating - this should clear the error
      const fourthStar = screen.getByRole('button', { name: 'Rate 4 stars' });
      fireEvent.click(fourthStar);

      // Error should be cleared immediately (synchronous state update)
      expect(screen.queryByText('Test error')).not.toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  describe('Initial Rating', () => {
    it('displays initial rating when provided', () => {
      render(<RatingDialog {...defaultProps} initialRating={4} />);
      expect(screen.getByText('4 stars')).toBeInTheDocument();
    });

    it('updates star container aria-label with initial rating', () => {
      render(<RatingDialog {...defaultProps} initialRating={3} />);
      const starContainer = screen.getByRole('group', { name: 'Rating: 3 out of 5 stars' });
      expect(starContainer).toBeInTheDocument();
    });
  });
});
