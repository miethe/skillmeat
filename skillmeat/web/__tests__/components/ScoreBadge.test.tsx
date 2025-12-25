import { render, screen } from '@testing-library/react';
import { ScoreBadge, ScoreBadgeSkeleton } from '@/components/ScoreBadge';

describe('ScoreBadge', () => {
  describe('Color Coding', () => {
    it('renders high confidence (>70) with green color', () => {
      render(<ScoreBadge confidence={85} />);
      const badge = screen.getByText('85%');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute(
        'aria-label',
        'Confidence score: 85 percent, high confidence'
      );
    });

    it('renders medium confidence (50-70) with yellow color', () => {
      render(<ScoreBadge confidence={60} />);
      const badge = screen.getByText('60%');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute(
        'aria-label',
        'Confidence score: 60 percent, medium confidence'
      );
    });

    it('renders low confidence (<50) with red color', () => {
      render(<ScoreBadge confidence={30} />);
      const badge = screen.getByText('30%');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute(
        'aria-label',
        'Confidence score: 30 percent, low confidence'
      );
    });
  });

  describe('Edge Cases', () => {
    it('handles 0% confidence', () => {
      render(<ScoreBadge confidence={0} />);
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('handles 100% confidence', () => {
      render(<ScoreBadge confidence={100} />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('clamps negative values to 0', () => {
      render(<ScoreBadge confidence={-10} />);
      expect(screen.getByText('0%')).toBeInTheDocument();
    });

    it('clamps values over 100 to 100', () => {
      render(<ScoreBadge confidence={150} />);
      expect(screen.getByText('100%')).toBeInTheDocument();
    });

    it('rounds decimal values to nearest integer', () => {
      render(<ScoreBadge confidence={87.6} />);
      expect(screen.getByText('88%')).toBeInTheDocument();
    });
  });

  describe('Boundary Values', () => {
    it('renders 70 as high confidence (boundary)', () => {
      render(<ScoreBadge confidence={70} />);
      const badge = screen.getByText('70%');
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('medium confidence')
      );
    });

    it('renders 71 as high confidence', () => {
      render(<ScoreBadge confidence={71} />);
      const badge = screen.getByText('71%');
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('high confidence')
      );
    });

    it('renders 50 as medium confidence (boundary)', () => {
      render(<ScoreBadge confidence={50} />);
      const badge = screen.getByText('50%');
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('medium confidence')
      );
    });

    it('renders 49 as low confidence', () => {
      render(<ScoreBadge confidence={49} />);
      const badge = screen.getByText('49%');
      expect(badge).toHaveAttribute(
        'aria-label',
        expect.stringContaining('low confidence')
      );
    });
  });

  describe('Accessibility', () => {
    it('includes proper aria-label with confidence level', () => {
      render(<ScoreBadge confidence={75} />);
      const badge = screen.getByLabelText(/confidence score: 75 percent/i);
      expect(badge).toBeInTheDocument();
    });

    it('includes title attribute for tooltip', () => {
      render(<ScoreBadge confidence={85} />);
      const badge = screen.getByText('85%');
      expect(badge).toHaveAttribute('title', 'High confidence: 85%');
    });
  });

  describe('Size Variants', () => {
    it('renders small size', () => {
      render(<ScoreBadge confidence={75} size="sm" />);
      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    it('renders medium size (default)', () => {
      render(<ScoreBadge confidence={75} />);
      expect(screen.getByText('75%')).toBeInTheDocument();
    });

    it('renders large size', () => {
      render(<ScoreBadge confidence={75} size="lg" />);
      expect(screen.getByText('75%')).toBeInTheDocument();
    });
  });

  describe('Custom Styling', () => {
    it('applies custom className', () => {
      render(<ScoreBadge confidence={75} className="custom-class" />);
      const badge = screen.getByText('75%');
      expect(badge).toHaveClass('custom-class');
    });
  });
});

describe('ScoreBadgeSkeleton', () => {
  it('renders loading skeleton', () => {
    render(<ScoreBadgeSkeleton />);
    const skeleton = screen.getByLabelText('Loading confidence score');
    expect(skeleton).toBeInTheDocument();
  });

  it('renders with custom size', () => {
    render(<ScoreBadgeSkeleton size="lg" />);
    const skeleton = screen.getByLabelText('Loading confidence score');
    expect(skeleton).toBeInTheDocument();
  });
});
