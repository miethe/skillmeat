/**
 * @jest-environment jsdom
 */
import { render, screen } from '@testing-library/react';
import { SimilarityBadge } from '@/components/marketplace/similarity-badge';
import type { SimilarityThresholds, SimilarityColors } from '@/types/similarity';

// ============================================================================
// Fixtures
// ============================================================================

const defaultThresholds: SimilarityThresholds = {
  high: 0.80,
  partial: 0.55,
  low: 0.35,
  floor: 0.20,
};

const defaultColors: SimilarityColors = {
  high: '#22c55e',    // green-500
  partial: '#eab308', // yellow-500
  low: '#f97316',     // orange-500
};

function renderBadge(
  score: number,
  thresholds: SimilarityThresholds = defaultThresholds,
  colors: SimilarityColors = defaultColors
) {
  return render(
    <SimilarityBadge score={score} thresholds={thresholds} colors={colors} />
  );
}

// ============================================================================
// Tests
// ============================================================================

describe('SimilarityBadge', () => {
  describe('High match band', () => {
    it('renders "High Match" label for score at high threshold', () => {
      renderBadge(0.80);
      expect(screen.getByText('High Match')).toBeInTheDocument();
    });

    it('renders "High Match" label for score above high threshold', () => {
      renderBadge(0.95);
      expect(screen.getByText('High Match')).toBeInTheDocument();
    });

    it('renders "High Match" label for score of 1.0', () => {
      renderBadge(1.0);
      expect(screen.getByText('High Match')).toBeInTheDocument();
    });

    it('displays score percentage for high match', () => {
      renderBadge(0.87);
      expect(screen.getByText('87%')).toBeInTheDocument();
    });

    it('applies the high color to the badge', () => {
      renderBadge(0.90);
      // The Badge primitive applies colorStyle as inline style background-color
      const el = document.querySelector('[aria-label]') as HTMLElement;
      expect(el?.style.backgroundColor).toBe('rgb(34, 197, 94)'); // #22c55e
    });

    it('has correct aria-label for high match', () => {
      renderBadge(0.87);
      expect(screen.getByLabelText('High similarity: 87%')).toBeInTheDocument();
    });
  });

  describe('Partial match band', () => {
    it('renders "Partial Match" label for score at partial threshold', () => {
      renderBadge(0.55);
      expect(screen.getByText('Partial Match')).toBeInTheDocument();
    });

    it('renders "Partial Match" label for score between partial and high', () => {
      renderBadge(0.72);
      expect(screen.getByText('Partial Match')).toBeInTheDocument();
    });

    it('displays score percentage for partial match', () => {
      renderBadge(0.64);
      expect(screen.getByText('64%')).toBeInTheDocument();
    });

    it('has correct aria-label for partial match', () => {
      renderBadge(0.64);
      expect(screen.getByLabelText('Partial similarity: 64%')).toBeInTheDocument();
    });
  });

  describe('Low match band', () => {
    it('renders "Low Match" label for score at low threshold', () => {
      renderBadge(0.35);
      expect(screen.getByText('Low Match')).toBeInTheDocument();
    });

    it('renders "Low Match" label for score between low and partial', () => {
      renderBadge(0.45);
      expect(screen.getByText('Low Match')).toBeInTheDocument();
    });

    it('displays score percentage for low match', () => {
      renderBadge(0.40);
      expect(screen.getByText('40%')).toBeInTheDocument();
    });

    it('has correct aria-label for low match', () => {
      renderBadge(0.40);
      expect(screen.getByLabelText('Low similarity: 40%')).toBeInTheDocument();
    });
  });

  describe('Below floor — renders nothing', () => {
    it('returns null for score below floor', () => {
      const { container } = renderBadge(0.10);
      expect(container.firstChild).toBeNull();
    });

    it('returns null for score of exactly 0', () => {
      const { container } = renderBadge(0);
      expect(container.firstChild).toBeNull();
    });

    it('returns null for score just below floor (0.19)', () => {
      const { container } = renderBadge(0.19);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('Between floor and low — renders nothing', () => {
    it('returns null for score at floor (0.20) when no low band matches', () => {
      // floor=0.20, low=0.35: scores [0.20, 0.34] are between floor and low
      const { container } = renderBadge(0.20);
      expect(container.firstChild).toBeNull();
    });

    it('returns null for score between floor and low (0.27)', () => {
      const { container } = renderBadge(0.27);
      expect(container.firstChild).toBeNull();
    });

    it('returns null for score just below low threshold (0.34)', () => {
      const { container } = renderBadge(0.34);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('Aria-label format', () => {
    it('includes level name and percentage in aria-label', () => {
      renderBadge(0.87);
      const badge = screen.getByLabelText('High similarity: 87%');
      expect(badge).toBeInTheDocument();
    });

    it('rounds percentage correctly — 0.875 rounds to 88%', () => {
      renderBadge(0.875);
      expect(screen.getByLabelText('High similarity: 88%')).toBeInTheDocument();
    });

    it('formats 1.0 score as 100%', () => {
      renderBadge(1.0);
      expect(screen.getByLabelText('High similarity: 100%')).toBeInTheDocument();
    });

    it('formats score close to threshold boundary correctly', () => {
      renderBadge(0.55);
      expect(screen.getByLabelText('Partial similarity: 55%')).toBeInTheDocument();
    });
  });

  describe('Custom thresholds', () => {
    it('respects custom high threshold', () => {
      const customThresholds: SimilarityThresholds = { high: 0.90, partial: 0.60, low: 0.40, floor: 0.25 };
      // 0.85 is below custom high (0.90), should fall into partial
      renderBadge(0.85, customThresholds);
      expect(screen.getByText('Partial Match')).toBeInTheDocument();
    });

    it('respects custom floor — score above floor but below low renders nothing', () => {
      const customThresholds: SimilarityThresholds = { high: 0.80, partial: 0.55, low: 0.50, floor: 0.30 };
      // 0.40 is above custom floor (0.30) but below custom low (0.50)
      const { container } = renderBadge(0.40, customThresholds);
      expect(container.firstChild).toBeNull();
    });
  });

  describe('className passthrough', () => {
    it('applies additional className to the badge', () => {
      render(
        <SimilarityBadge
          score={0.90}
          thresholds={defaultThresholds}
          colors={defaultColors}
          className="my-custom-class"
        />
      );
      const badge = screen.getByLabelText('High similarity: 90%');
      expect(badge).toHaveClass('my-custom-class');
    });
  });
});
