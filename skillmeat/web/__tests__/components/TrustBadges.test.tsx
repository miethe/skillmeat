/**
 * Tests for TrustBadges component
 */

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TrustBadges, getTrustLevelFromSource } from '@/components/TrustBadges';

describe('TrustBadges', () => {
  describe('Official badge', () => {
    it('renders official badge with correct styling', () => {
      render(<TrustBadges trustLevel="official" />);
      const badge = screen.getByText('Official');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute('aria-label', 'Official artifact from trusted source');
    });

    it('shows tooltip on hover', async () => {
      const user = userEvent.setup();
      render(<TrustBadges trustLevel="official" />);

      const badge = screen.getByText('Official');
      await user.hover(badge);

      // Wait for tooltip to appear (using getAllByText for duplicate elements)
      const tooltips = await screen.findAllByText('Official artifact from trusted source');
      expect(tooltips.length).toBeGreaterThan(0);
    });

    it('displays source in tooltip when provided', async () => {
      const user = userEvent.setup();
      render(<TrustBadges trustLevel="official" source="anthropics/skills/canvas" />);

      const badge = screen.getByText('Official');
      await user.hover(badge);

      const sourceText = await screen.findAllByText(/Source: anthropics\/skills\/canvas/);
      expect(sourceText.length).toBeGreaterThan(0);
    });
  });

  describe('Verified badge', () => {
    it('renders verified badge with correct styling', () => {
      render(<TrustBadges trustLevel="verified" />);
      const badge = screen.getByText('Verified');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute('aria-label', 'Community verified artifact');
    });

    it('shows tooltip on hover', async () => {
      const user = userEvent.setup();
      render(<TrustBadges trustLevel="verified" />);

      const badge = screen.getByText('Verified');
      await user.hover(badge);

      const tooltips = await screen.findAllByText('Community verified artifact');
      expect(tooltips.length).toBeGreaterThan(0);
    });
  });

  describe('Community badge', () => {
    it('renders community badge with correct styling', () => {
      render(<TrustBadges trustLevel="community" />);
      const badge = screen.getByText('Community');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute('aria-label', 'Community contributed artifact');
    });

    it('shows tooltip on hover', async () => {
      const user = userEvent.setup();
      render(<TrustBadges trustLevel="community" />);

      const badge = screen.getByText('Community');
      await user.hover(badge);

      const tooltips = await screen.findAllByText('Community contributed artifact');
      expect(tooltips.length).toBeGreaterThan(0);
    });
  });

  describe('Custom className', () => {
    it('applies custom className', () => {
      render(<TrustBadges trustLevel="official" className="custom-class" />);
      const badge = screen.getByText('Official');
      expect(badge).toHaveClass('custom-class');
    });
  });
});

describe('getTrustLevelFromSource', () => {
  describe('Official sources', () => {
    it('identifies anthropic/ as official', () => {
      expect(getTrustLevelFromSource('anthropic/skills/canvas')).toBe('official');
    });

    it('identifies anthropics/ as official', () => {
      expect(getTrustLevelFromSource('anthropics/skills/document')).toBe('official');
    });

    it('identifies claude- prefix as official', () => {
      expect(getTrustLevelFromSource('claude-marketplace/skill')).toBe('official');
    });

    it('is case insensitive for official patterns', () => {
      expect(getTrustLevelFromSource('ANTHROPIC/skills/test')).toBe('official');
      expect(getTrustLevelFromSource('Anthropics/agents/test')).toBe('official');
      expect(getTrustLevelFromSource('CLAUDE-test/skill')).toBe('official');
    });

    it('matches anthropic in path, not just prefix', () => {
      expect(getTrustLevelFromSource('github.com/anthropics/skills')).toBe('official');
    });
  });

  describe('Verified sources', () => {
    it('identifies verified/ prefix as verified', () => {
      expect(getTrustLevelFromSource('verified/user/repo/skill')).toBe('verified');
    });

    it('identifies trusted- prefix as verified', () => {
      expect(getTrustLevelFromSource('trusted-user/repo')).toBe('verified');
    });

    it('is case insensitive for verified patterns', () => {
      expect(getTrustLevelFromSource('VERIFIED/test/repo')).toBe('verified');
      expect(getTrustLevelFromSource('Trusted-Test/skill')).toBe('verified');
    });
  });

  describe('Community sources', () => {
    it('identifies regular GitHub URLs as community', () => {
      expect(getTrustLevelFromSource('user/repo/skill')).toBe('community');
    });

    it('identifies non-matching sources as community', () => {
      expect(getTrustLevelFromSource('random-source/test')).toBe('community');
    });

    it('handles empty strings as community', () => {
      expect(getTrustLevelFromSource('')).toBe('community');
    });
  });

  describe('Edge cases', () => {
    it('prioritizes official over verified', () => {
      // If a source somehow matches both patterns, official should win
      expect(getTrustLevelFromSource('anthropic/verified/skill')).toBe('official');
    });

    it('handles URLs with protocols', () => {
      expect(getTrustLevelFromSource('https://github.com/anthropics/skills')).toBe('official');
      // Note: https://verified/ doesn't start with verified/, so it's community
      expect(getTrustLevelFromSource('verified/user/repo')).toBe('verified');
    });
  });
});
