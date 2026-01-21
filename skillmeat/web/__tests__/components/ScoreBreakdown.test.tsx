/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ScoreBreakdown } from '@/components/ScoreBreakdown';

describe('ScoreBreakdown', () => {
  const defaultProps = {
    confidence: 92,
    trust: 95,
    quality: 87,
    match: 92,
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Rendering', () => {
    it('renders the trigger button', () => {
      render(<ScoreBreakdown {...defaultProps} />);
      expect(screen.getByRole('button', { name: /show score breakdown/i })).toBeInTheDocument();
    });

    it('renders collapsed by default', () => {
      render(<ScoreBreakdown {...defaultProps} />);
      expect(screen.queryByText(/Source trustworthiness/i)).not.toBeInTheDocument();
    });

    it('renders expanded when defaultExpanded is true', () => {
      render(<ScoreBreakdown {...defaultProps} defaultExpanded={true} />);
      expect(screen.getByText(/Source trustworthiness/i)).toBeInTheDocument();
      expect(screen.getByText(/User ratings \+ maintenance/i)).toBeInTheDocument();
      expect(screen.getByText(/Relevance to your query/i)).toBeInTheDocument();
    });

    it('applies custom className', () => {
      const { container } = render(<ScoreBreakdown {...defaultProps} className="custom-class" />);
      expect(container.firstChild).toHaveClass('custom-class');
    });
  });

  describe('Expansion/Collapse', () => {
    it('expands when trigger is clicked', async () => {
      const user = userEvent.setup();
      render(<ScoreBreakdown {...defaultProps} />);

      const trigger = screen.getByRole('button', { name: /show score breakdown/i });
      await user.click(trigger);

      expect(screen.getByText(/Source trustworthiness/i)).toBeInTheDocument();
    });

    it('collapses when trigger is clicked again', async () => {
      const user = userEvent.setup();
      render(<ScoreBreakdown {...defaultProps} defaultExpanded={true} />);

      const trigger = screen.getByRole('button', { name: /hide score breakdown/i });
      await user.click(trigger);

      expect(screen.queryByText(/Source trustworthiness/i)).not.toBeInTheDocument();
    });

    it('toggles chevron rotation on expand/collapse', async () => {
      const user = userEvent.setup();
      render(<ScoreBreakdown {...defaultProps} />);

      const trigger = screen.getByRole('button', { name: /show score breakdown/i });
      const chevron = trigger.querySelector('svg');

      // Initially not rotated
      expect(chevron).not.toHaveClass('rotate-180');

      // Expand
      await user.click(trigger);
      expect(chevron).toHaveClass('rotate-180');

      // Collapse
      await user.click(trigger);
      expect(chevron).not.toHaveClass('rotate-180');
    });
  });

  describe('Score Components Display', () => {
    beforeEach(() => {
      render(<ScoreBreakdown {...defaultProps} defaultExpanded={true} />);
    });

    it('displays all three score components', () => {
      expect(screen.getByText('Trust')).toBeInTheDocument();
      expect(screen.getByText('Quality')).toBeInTheDocument();
      expect(screen.getByText('Match')).toBeInTheDocument();
    });

    it('displays correct scores', () => {
      expect(screen.getByText(/95/)).toBeInTheDocument(); // Trust
      expect(screen.getByText(/87/)).toBeInTheDocument(); // Quality
      // 92 appears twice: in Match component and in formula
      expect(screen.getAllByText(/92/).length).toBeGreaterThanOrEqual(1);
    });

    it('displays default weights as percentages', () => {
      expect(screen.getAllByText(/\(25%\)/)).toHaveLength(2); // Trust and Quality
      expect(screen.getByText(/\(50%\)/)).toBeInTheDocument(); // Match
    });

    it('displays component descriptions', () => {
      expect(screen.getByText('Source trustworthiness')).toBeInTheDocument();
      expect(screen.getByText('User ratings + maintenance')).toBeInTheDocument();
      expect(screen.getByText('Relevance to your query')).toBeInTheDocument();
    });
  });

  describe('Custom Weights', () => {
    it('displays custom weights correctly', () => {
      const customWeights = {
        trust: 0.3,
        quality: 0.2,
        match: 0.5,
      };

      render(<ScoreBreakdown {...defaultProps} weights={customWeights} defaultExpanded={true} />);

      expect(screen.getByText(/\(30%\)/)).toBeInTheDocument(); // Trust
      expect(screen.getByText(/\(20%\)/)).toBeInTheDocument(); // Quality
      expect(screen.getByText(/\(50%\)/)).toBeInTheDocument(); // Match
    });

    it('displays custom weights in formula', () => {
      const customWeights = {
        trust: 0.3,
        quality: 0.2,
        match: 0.5,
      };

      render(<ScoreBreakdown {...defaultProps} weights={customWeights} defaultExpanded={true} />);

      expect(screen.getByText(/Formula:/)).toBeInTheDocument();
      expect(screen.getByText(/\(T×0\.3\) \+ \(Q×0\.2\) \+ \(M×0\.5\)/)).toBeInTheDocument();
    });
  });

  describe('Formula Display', () => {
    it('displays the formula with confidence score', () => {
      render(<ScoreBreakdown {...defaultProps} defaultExpanded={true} />);

      const formula = screen.getByText(/Formula:/);
      expect(formula).toBeInTheDocument();
      expect(screen.getByText(/= 92%/)).toBeInTheDocument();
    });

    it('includes all weight components in formula', () => {
      render(<ScoreBreakdown {...defaultProps} defaultExpanded={true} />);

      expect(screen.getByText(/\(T×0\.25\)/)).toBeInTheDocument();
      expect(screen.getByText(/\(Q×0\.25\)/)).toBeInTheDocument();
      expect(screen.getByText(/\(M×0\.5\)/)).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('has accessible trigger button', () => {
      render(<ScoreBreakdown {...defaultProps} />);
      const trigger = screen.getByRole('button', { name: /show score breakdown/i });
      expect(trigger).toBeInTheDocument();
    });

    it('updates aria-label when expanded', async () => {
      const user = userEvent.setup();
      render(<ScoreBreakdown {...defaultProps} />);

      const trigger = screen.getByRole('button', { name: /show score breakdown/i });
      await user.click(trigger);

      expect(screen.getByRole('button', { name: /hide score breakdown/i })).toBeInTheDocument();
    });

    it('progress bars have aria-labels', () => {
      render(<ScoreBreakdown {...defaultProps} defaultExpanded={true} />);

      expect(screen.getByLabelText('Trust score: 95 out of 100')).toBeInTheDocument();
      expect(screen.getByLabelText('Quality score: 87 out of 100')).toBeInTheDocument();
      expect(screen.getByLabelText('Match score: 92 out of 100')).toBeInTheDocument();
    });

    it('progress bars have aria-value attributes', () => {
      render(<ScoreBreakdown {...defaultProps} defaultExpanded={true} />);

      const trustProgress = screen.getByLabelText('Trust score: 95 out of 100');
      expect(trustProgress).toHaveAttribute('aria-valuemin', '0');
      expect(trustProgress).toHaveAttribute('aria-valuemax', '100');
      expect(trustProgress).toHaveAttribute('aria-valuenow', '95');
    });

    it('is keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<ScoreBreakdown {...defaultProps} />);

      const trigger = screen.getByRole('button', { name: /show score breakdown/i });

      // Focus the trigger
      trigger.focus();
      expect(trigger).toHaveFocus();

      // Press Enter to expand
      await user.keyboard('{Enter}');
      expect(screen.getByText(/Source trustworthiness/i)).toBeInTheDocument();

      // Press Space to collapse
      await user.keyboard(' ');
      expect(screen.queryByText(/Source trustworthiness/i)).not.toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles zero scores', () => {
      render(
        <ScoreBreakdown confidence={0} trust={0} quality={0} match={0} defaultExpanded={true} />
      );

      expect(screen.getAllByText(/\b0\b/)).toHaveLength(4); // 3 components + confidence in formula
    });

    it('handles perfect scores', () => {
      render(
        <ScoreBreakdown
          confidence={100}
          trust={100}
          quality={100}
          match={100}
          defaultExpanded={true}
        />
      );

      expect(screen.getAllByText(/\b100\b/)).toHaveLength(4); // 3 components + confidence in formula
    });

    it('handles decimal scores by rounding in weight percentages', () => {
      const decimalWeights = {
        trust: 0.333,
        quality: 0.333,
        match: 0.334,
      };

      render(<ScoreBreakdown {...defaultProps} weights={decimalWeights} defaultExpanded={true} />);

      // Math.round(0.333 * 100) = 33
      // Math.round(0.334 * 100) = 33
      expect(screen.getAllByText(/\(33%\)/)).toHaveLength(3);
    });
  });
});
